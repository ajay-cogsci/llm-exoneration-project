import argparse
import json
import os
import sys

from .api import APIError, OpenAIResponses
from .io import read_json
from .pipeline import generate_run, inspect_configuration, sample_run


def main(argv=None):
    parser = argparse.ArgumentParser(description="PhD semi-synthetic profile sampling and constrained API CV generation")
    sub = parser.add_subparsers(dest="command", required=True)
    inspect = sub.add_parser("inspect", help="Review configuration and sources without sampling, writing files or calling an API")
    inspect.add_argument("--config", default="configs/phd.json")
    sample = sub.add_parser("sample", help="Sample and validate structured profiles without API calls")
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
