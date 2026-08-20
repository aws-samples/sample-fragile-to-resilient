"""Student runner for the extraction pipeline.

You do NOT need to edit this file. Run it from the command line to feed a
document through the extraction pipeline and see the result.

Examples:
    # Extract the clean submission (should succeed on the first try):
    python run.py clean

    # Extract the rule-violating submission (watch the repair loop fix it):
    python run.py violating

    # Give the pipeline NO repair budget, so a bad document fails loudly:
    python run.py violating --max-repairs 0
"""

import argparse
import sys
from pathlib import Path

from fde.extraction import ExtractionError, extract_policy

DOCUMENTS = {
    "clean": "documents/clean-submission.txt",
    "violating": "documents/rule-violating-submission.txt",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the extraction pipeline.")
    parser.add_argument(
        "document",
        choices=DOCUMENTS.keys(),
        help="Which sample document to extract.",
    )
    parser.add_argument(
        "--max-repairs",
        type=int,
        default=2,
        help=(
            "How many times the pipeline may re-ask the model on failure (default: 2)."
        ),
    )
    args = parser.parse_args()

    path = Path(DOCUMENTS[args.document])
    document = path.read_text()

    max_calls = 1 + args.max_repairs
    print(f"Extracting: {path}")
    print(f"Repair budget: {args.max_repairs} retries")
    print(
        f"NOTE: this invokes Amazon Bedrock and incurs charges on your AWS "
        f"account (up to {max_calls} model call(s), billed per token).\n"
    )

    try:
        policy = extract_policy(document, max_repairs=args.max_repairs)
    except ExtractionError as err:
        print(f"FAILED after {err.attempts} attempt(s): {err}")
        print(f"  why it failed : {err.validation_errors}")
        print(f"  last raw output: {err.last_raw}")
        sys.exit(1)

    print("SUCCESS — extracted a validated PolicySubmission:\n")
    print(policy.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
