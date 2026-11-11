import argparse
import json
import os
import sys

from .api import APIError, OpenAIResponses
from .io import read_json
from .pipeline import generate_run, inspect_configuration, sample_run
from .rubric_pipeline import audit_existing, inspect_revision, sample_revision


def main(argv=None):
    parser = argparse.ArgumentParser(description="PhD semi-synthetic profile sampling and constrained API CV generation")
    sub = parser.add_subparsers(dest="command", required=True)
    inspect = sub.add_parser("inspect", help="Inspect legacy v2 settings; use inspect-rubric for the revised pipeline")
    inspect.add_argument("--config", default="configs/phd.json")
    sample = sub.add_parser("sample", help="Legacy v2 quintile sampler; use sample-rubric for corrected tiers")
    sample.add_argument("--config", default="configs/phd.json")
    sample.add_argument("--out", required=True)
    sample.add_argument("--n-per-cohort", type=int)
    sample.add_argument("--oversample", type=int)
    generate = sub.add_parser("generate", help="Generate and fact-check a bounded batch of CVs via OpenAI")
    generate.add_argument("--run", required=True)
    generate.add_argument("--limit", type=int, required=True, help="Maximum profiles selected, including cached profiles")
    generate.add_argument("--model")
    generate.add_argument("--review-model")
    generate.add_argument("--batch", default="generation")
    for name, help_text in (
        ("inspect-rubric", "Inspect the provisional rubric and conditional sampler; no data or API calls"),
        ("audit-rubric", "Audit existing CVs and pool; save proposed labels and blind human review materials"),
        ("sample-rubric", "Create a NEW structured sample only with an explicitly configured allocation"),
    ):
        command = sub.add_parser(name, help=help_text)
        command.add_argument("--config", default="configs/phd.json", help="Legacy base settings reused for timelines and research fields")
        command.add_argument("--rubric", default="configs/phd_rubric_v1.json")
        command.add_argument("--sampling-policy", default="configs/phd_sampling_v3.json")
        if name != "inspect-rubric":
            command.add_argument("--out", required=True)
        if name == "audit-rubric":
            command.add_argument("--source", default="sample-100-resume-generated")
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            result = inspect_configuration(read_json(args.config))
        elif args.command == "sample":
            config = read_json(args.config)
            if args.n_per_cohort is not None:
                config["n_per_cohort"] = args.n_per_cohort
            if args.oversample is not None:
                config["oversample"] = args.oversample
            result = sample_run(config, args.out)
        elif args.command in {"inspect-rubric", "audit-rubric", "sample-rubric"}:
            config, rubric, sampling = read_json(args.config), read_json(args.rubric), read_json(args.sampling_policy)
            if args.command == "inspect-rubric":
                result = inspect_revision(config, rubric, sampling)
            elif args.command == "audit-rubric":
                result = audit_existing(args.source, args.out, config, rubric, sampling)
            else:
                result = sample_revision(config, rubric, sampling, args.out)
        else:
            config = read_json(os.path.join(args.run, "config.json"))
            model = args.model or os.getenv("OPENAI_MODEL") or config["generation"]["model"]
            reviewer = args.review_model or os.getenv("OPENAI_REVIEW_MODEL") or config["generation"]["review_model"] or model
            if not model:
                raise ValueError("Choose a model with --model, OPENAI_MODEL, or generation.model in the run configuration")
            result = generate_run(args.run, OpenAIResponses(), model, reviewer, args.limit, args.batch)
        print(json.dumps({k: v for k, v in result.items() if k != "profiles" or isinstance(v, int)}, indent=2))
        return 0
    except (APIError, ValueError, KeyError, FileNotFoundError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
