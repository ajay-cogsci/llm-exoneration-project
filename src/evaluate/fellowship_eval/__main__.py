"""python3 -m fellowship_eval: preview, plan, verify-plan, run, collect."""

import argparse
import json
import sys

from phd_resumes.io import read_json
from .design import load_applicants, messages
from .run import APIError, OpenRouter, collect, execute, load_plan, make_plan


def split(value):
    return value.split(",") if value else None


def main(argv=None):
    parser = argparse.ArgumentParser(description="Fellowship extension: offline preparation and separately approved evaluation")
    sub = parser.add_subparsers(dest="command", required=True)
    preview = sub.add_parser("preview", help="Print an assembled prompt; no API calls")
    preview.add_argument("--config", default="configs/fellowship_eval_v1.json")
    preview.add_argument("--applicant")
    preview.add_argument("--condition", default="clean")
    preview.add_argument("--wording", type=int, default=1)
    preview.add_argument("--task", default="quality")
    preview.add_argument("--format", default="answer_only")
    plan = sub.add_parser("plan", help="Freeze a new plan; no API calls")
    plan.add_argument("--config", default="configs/fellowship_eval_v1.json")
    plan.add_argument("--out", required=True)
    plan.add_argument("--per-tier", type=int)
    for name in ("conditions", "wordings", "tasks", "formats"):
        plan.add_argument("--" + name)
    plan.add_argument("--repeats", type=int, default=1)
    check = sub.add_parser("verify-plan", help="Check frozen plan and input hashes; no API calls")
    check.add_argument("--plan", required=True)
    run = sub.add_parser("run", help="Billable: requires an approved budget and verified worst-case request cost")
    run.add_argument("--plan", required=True)
    run.add_argument("--label", required=True)
    run.add_argument("--api-model", required=True)
    run.add_argument("--budget-cap-usd", required=True, type=float)
    run.add_argument("--request-cost-ceiling-usd", required=True, type=float)
    run.add_argument("--limit", type=int)
    run.add_argument("--concurrency", type=int, default=1)
    run.add_argument("--max-attempts", type=int, default=2)
    run.add_argument("--conditions", help="Dispatch only these conditions from the same frozen plan, e.g. clean")
    export = sub.add_parser("collect", help="Export eventual and first-attempt replies; no API calls")
    export.add_argument("--plan", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "preview":
            config = read_json(args.config)
            applicants = load_applicants(config)
            applicant = next((a for a in applicants if a["applicant_id"] == args.applicant), None) if args.applicant else applicants[0]
            if applicant is None:
                raise ValueError("Unknown fellowship applicant")
            for message in messages(config, applicant, args.condition, args.wording, args.task, args.format):
                print(f"===== {message['role'].upper()} =====\n{message['content']}\n")
            return 0
        if args.command == "plan":
            result = make_plan(read_json(args.config), args.out, per_tier=args.per_tier,
                               conditions=split(args.conditions), wordings=[int(x) for x in split(args.wordings)] if args.wordings else None,
                               tasks=split(args.tasks), formats=split(args.formats), repeats=args.repeats)
        elif args.command == "verify-plan":
            config, design, applicants = load_plan(args.plan)
            result = {"verified": True, "requests_per_model": len(design),
                      "applicants": len({r["applicant_id"] for r in design}), "api_calls": 0,
                      "opportunity": config["opportunity"]["id"]}
        elif args.command == "run":
            result = execute(args.plan, OpenRouter(), args.label, args.api_model,
                             budget_cap=args.budget_cap_usd, request_cost_ceiling=args.request_cost_ceiling_usd,
                             limit=args.limit, concurrency=args.concurrency, max_attempts=args.max_attempts,
                             conditions=split(args.conditions))
        else:
            result = collect(args.plan)
        print(json.dumps(result, indent=2))
        return 2 if result.get("stop_reasons") else 0
    except (APIError, ValueError, KeyError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
