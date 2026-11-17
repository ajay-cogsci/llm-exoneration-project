"""Prepare, generate, export or verify a versioned graduate TA dataset."""

import argparse
import json

from phd_resumes.io import read_json
from .pipeline import export, generate, prepare, verify_export


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sampling = sub.add_parser("prepare")
    sampling.add_argument("--config", default="configs/ta_v1.json")
    sampling.add_argument("--run", required=True)
    generation = sub.add_parser("generate")
    generation.add_argument("--run", required=True)
    generation.add_argument("--limit", type=int)
    packaging = sub.add_parser("export")
    packaging.add_argument("--run", required=True)
    packaging.add_argument("--out", required=True)
    verification = sub.add_parser("verify")
    verification.add_argument("--out", required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(read_json(args.config), args.run)
    elif args.command == "generate":
        result = generate(args.run, limit=args.limit)
    elif args.command == "export":
        result = export(args.run, args.out)
    else:
        result = verify_export(args.out)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
