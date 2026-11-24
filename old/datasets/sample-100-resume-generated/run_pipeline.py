"""Run the existing pipeline for an authorized 100-resume validation sample.

The library, sampling parameters, prompts, and validators are unchanged. Three
independent output directories allow bounded concurrency and preserve caching.
No credentials are loaded from files or written to outputs.
"""

import argparse
import copy
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))

from phd_resumes.api import APIError, OpenAIResponses
from phd_resumes.io import digest, implementation_hash, read_json, write_json
from phd_resumes.pipeline import generate_run, sample_run, utc_now

COHORTS = [(123, 33, 17), (456, 33, 16), (789, 34, 17)]
MODEL = "gpt-6-astra"


class StoppableClient(OpenAIResponses):
    def create(self, body):
        if (ROOT / "STOP").exists():
            raise APIError("Run stopped before the next API call; existing responses are preserved")
        return super().create(body)


def prepare():
    original = read_json(ROOT.parent / "configs/phd.json")
    plan = {
        "created_at": utc_now(),
        "purpose": "User-authorized live validation with 100 PhD applicant resumes",
        "model": MODEL,
        "review_model": MODEL,
        "model_source": "https://developers.openai.com/api/docs/models/gpt-6-astra",
        "model_selection": "Quality-first reasoning model with Responses and Structured Outputs support; account access verified.",
        "baseline_config_hash": digest(original),
        "implementation_hash": implementation_hash(),
        "expected_selected": 100,
        "expected_pool": 150,
        "max_parallel_cohorts": 3,
        "cohorts": [],
        "limits": [
            "Small validation sample; provisional PhD distributions are not empirically calibrated.",
            "Same-model review in a separate context is not independent-model or human validation.",
            "Cohort-relative strength labels are metadata and do not appear in resumes.",
            "The original pipeline does not automatically repair rejected CV content.",
        ],
    }
    if (ROOT / "run_plan.json").exists():
        raise ValueError("Run is already prepared; use --stage generate to resume")
    for seed, selected, oversample in COHORTS:
        config = copy.deepcopy(original)
        config.update(seeds=[seed], n_per_cohort=selected, oversample=oversample)
        config["generation"].update(model=MODEL, review_model=MODEL)
        directory = ROOT / "cohorts" / f"seed-{seed}"
        report = sample_run(config, directory)
        plan["cohorts"].append({"seed": seed, "path": str(directory.relative_to(ROOT)), **report})
        print(f"Prepared seed {seed}: {report}", flush=True)
    write_json(ROOT / "run_plan.json", plan)


def generate():
    plan = read_json(ROOT / "run_plan.json")
    if plan["implementation_hash"] != implementation_hash():
        raise ValueError("Pipeline implementation changed since sampling")
    results, failures = {}, {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        jobs = {
            executor.submit(
                generate_run, ROOT / cohort["path"], StoppableClient(),
                MODEL, MODEL, cohort["profiles"],
            ): str(cohort["seed"])
            for cohort in plan["cohorts"]
        }
        for job in as_completed(jobs):
            seed = jobs[job]
            try:
                summary = job.result()
                results[seed] = {
                    "status_counts": summary["status_counts"],
                    "usage": summary["usage_all_cached_responses_in_batch"],
                }
                print(f"Completed seed {seed}: {results[seed]}", flush=True)
            except Exception as exc:
                failures[seed] = {"type": type(exc).__name__, "message": str(exc)}
                print(f"Stopped seed {seed}: {type(exc).__name__}: {exc}", flush=True)
    write_json(ROOT / "first_pass_result.json", {
        "updated_at": utc_now(), "completed_cohorts": results, "failed_cohorts": failures,
    })
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=["prepare", "generate"], required=True)
    args = parser.parse_args()
    {"prepare": prepare, "generate": generate}[args.stage]()
