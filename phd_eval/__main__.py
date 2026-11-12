import argparse
import json
import sys

from phd_resumes.io import read_json

from .design import check_config, load_applicants, messages
from .run import APIError, ChatCompletions, collect, execute, make_plan


def split(value):
    return [item for item in value.split(",") if item] if value else None


def main(argv=None):
    parser = argparse.ArgumentParser(description="PhD exoneration evaluation: preview prompts, plan a design, run a model, export results")
    sub = parser.add_subparsers(dest="command", required=True)
    preview = sub.add_parser("preview", help="Print one fully assembled prompt; no API calls")
    preview.add_argument("--config", default="configs/phd_eval_v1.json")
    preview.add_argument("--applicant")
    preview.add_argument("--condition", default="clean")
    preview.add_argument("--wording", type=int, default=1)
    preview.add_argument("--task", default="quality")
    preview.add_argument("--format", default="answer_only")
    plan = sub.add_parser("plan", help="Write a new design; no API calls")
    plan.add_argument("--config", default="configs/phd_eval_v1.json")
    plan.add_argument("--out", required=True)
    plan.add_argument("--per-tier", type=int, help="Pilot: this many applicants from each CV tier (seeded)")
    plan.add_argument("--conditions", help="Comma-separated condition ids; default all. Must include clean")
    plan.add_argument("--wordings", help="Comma-separated wording numbers; default all")
    plan.add_argument("--tasks", help="Comma-separated task names; default all")
    plan.add_argument("--formats", help="Comma-separated formats; default all")
    plan.add_argument("--repeats", type=int, default=1)
    run = sub.add_parser("run", help="Send outstanding requests for one model; resumable")
    run.add_argument("--plan", required=True)
    run.add_argument("--label", required=True, help="Name used in results, e.g. 'GPT-5.5'")
    run.add_argument("--api-model", required=True, help="Model identifier expected by the endpoint")
    run.add_argument("--base-url", help="Chat-completions base URL; default EVAL_BASE_URL or OpenAI")
    run.add_argument("--param", action="append", default=[], help="Request parameter as key=JSON, e.g. temperature=1 (repeatable)")
    run.add_argument("--limit", type=int, help="Send at most this many requests now")
    run.add_argument("--concurrency", type=int, default=4)
    export = sub.add_parser("collect", help="Write results.csv and summary.json for a plan")
    export.add_argument("--plan", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "preview":
            config = read_json(args.config)
            check_config(config)
            applicants = load_applicants(config)
            applicant = next((a for a in applicants if a["applicant_id"] == args.applicant), None) if args.applicant else applicants[0]
            if applicant is None:
                raise ValueError("Unknown applicant")
            for message in messages(config, applicant, args.condition, args.wording, args.task, args.format):
                print(f"===== {message['role'].upper()} =====\n{message['content']}\n")
            return 0
        if args.command == "plan":
            result = make_plan(read_json(args.config), args.out, per_tier=args.per_tier, conditions=split(args.conditions), wordings=[int(w) for w in split(args.wordings)] if args.wordings else None, tasks=split(args.tasks), formats=split(args.formats), repeats=args.repeats)
        elif args.command == "run":
            parameters = {}
            for item in args.param:
                key, _, value = item.partition("=")
                parameters[key] = json.loads(value)
            result = execute(args.plan, ChatCompletions(args.base_url), args.label, args.api_model, parameters=parameters, limit=args.limit, concurrency=args.concurrency)
        else:
            result = collect(args.plan)
        print(json.dumps(result, indent=2))
        return 0
    except (APIError, ValueError, KeyError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
