import argparse
import json
import sys

from phd_resumes.io import read_json
from .pipeline import generate, verify


def main(argv=None):
    parser = argparse.ArgumentParser(description="Three fixed-template PhD recommendation summaries per existing applicant; no API calls")
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("generate", help="Write a new versioned recommendation package from accepted CVs")
    create.add_argument("--source", required=True)
    create.add_argument("--out", required=True)
    create.add_argument("--policy", default="configs/phd_recommendations_v1.json")
    create.add_argument("--applicant-id", action="append", help="Repeat to make a pilot subset; omission selects all source applicants")
    check = sub.add_parser("verify", help="Recheck saved records, templates, hashes and optionally the source run")
    check.add_argument("--run", required=True)
    check.add_argument("--source")
    args = parser.parse_args(argv)
    try:
        result = generate(args.source, args.out, read_json(args.policy), args.applicant_id) if args.command == "generate" else verify(args.run, args.source)
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, KeyError, TypeError, OSError, StopIteration) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
