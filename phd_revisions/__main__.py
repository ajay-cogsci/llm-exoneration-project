import argparse
import json
import sys

from phd_resumes.io import read_json
from .export import build


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build the corrected CV and application datasets from the published ones; no API calls")
    parser.add_argument("--datasets", default="datasets")
    parser.add_argument("--gpa-policy", default="configs/phd_gpa_consistency_v1.json")
    parser.add_argument("--recommendation-policy", default="configs/phd_recommendations_v2.json")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(build(args.datasets, read_json(args.gpa_policy), read_json(args.recommendation_policy)), indent=2))
        return 0
    except (ValueError, KeyError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
