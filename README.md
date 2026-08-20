# Student Starter Kit — From Fragile to Resilient

This kit is a small, complete Python project that turns unstructured insurance
documents into validated, typed data using Amazon Bedrock — and does it the way
production code has to: with retries, backoff, structured logging, bounded
concurrency, and a real command-line interface.

Everything is already written. You are not expected to write code — just to
read it, run it, and watch it work.

> ℹ️ **What this is:** teaching code. It demonstrates production *patterns* —
> retries, backoff, validation, bounded concurrency — but it ships demo-grade
> defaults and has not been hardened for production use. Learn the patterns
> here, then apply them in your own code with your own review. Nothing is
> provisioned and there is nothing to tear down: everything runs locally, and
> the only AWS resource involved is the Bedrock API itself.

## What's in here

| File / folder | What it is |
|---|---|
| `fde/bedrock_client.py` | The Bedrock client — connection, retry-on-transient-errors, exponential backoff, structured logging, and typed errors |
| `fde/models.py` | The Pydantic data contract that defines what a "valid" extraction looks like |
| `fde/extraction.py` | The extraction pipeline — prompt the model, validate the result, and repair it if validation fails |
| `fde/batch.py` | Concurrent batch summarization, capped by a semaphore so you don't stampede the API |
| `fde/cli.py` | The typed `summarize` CLI, built with typer |
| `scripts/throttle_demo.py` | Induced-throttling demo: watch retries, backoff, and give-up — **no AWS calls, free** |
| `scripts/batch_benchmark.py` | Concurrency benchmark: serial vs. capped async — **no AWS calls, free** |
| `tests/` | The full test suite (28 tests, zero AWS calls) |
| `documents/` | Two synthetic insurance submissions to feed the pipeline |
| `run.py` | A ready-made runner for the extraction pipeline — you do not edit this |
| `pyproject.toml` | Package metadata plus the `summarize` entry point |
| `requirements.txt` | The Python packages the code needs |

## Setup

Requires Python 3.12 or newer.

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\Activate.ps1     # Windows (PowerShell)

# 2. Install the dependencies
pip install -r requirements.txt

# 3. Install this kit as an editable package. This is what creates the
#    `summarize` command (the [project.scripts] entry point) and lets the
#    tests and scripts import `fde` from anywhere.
pip install -e .

# 4. Configure your AWS credentials and enable Bedrock model access in your
#    account. Only needed for the commands marked "incurs cost" below.
```

## Run the extraction pipeline

> ⚠️ **Cost notice:** These commands invoke a model on Amazon Bedrock and
> **incur charges** on your AWS account. Bedrock bills per token; the repair
> loop makes one call per attempt. Typically fractions of a cent for these
> short documents, but not zero — you are responsible for any charges.

```bash
# Clean document — succeeds on the first try (one model call):
python run.py clean

# Rule-violating document — watch the repair loop fix an impossible age:
python run.py violating

# No repair budget — see the pipeline fail loudly with a typed error:
python run.py violating --max-repairs 0
```

## Run the resilience and concurrency demos

Both of these fake the model entirely, so they cost nothing and work offline.

```bash
# Induced throttling — retries, backoff, and give-up. FREE, no AWS calls:
python scripts/throttle_demo.py

# Concurrency benchmark — serial vs. capped async. FREE, no AWS calls:
python scripts/batch_benchmark.py
```

## Run the CLI

`--help` and the missing-file path are free; summarizing a real document makes
one Bedrock call and **incurs cost**.

```bash
summarize --help
summarize missing.txt ; echo "exit code: $?"
summarize documents/clean-submission.txt
```

## Run the tests

The whole suite runs without AWS — every model call is faked:

```bash
pytest
```

Expect **28 passed** in under a second.

## Reading order

The code is easiest to follow in this order:

1. `fde/bedrock_client.py` — the connection, and the retry/backoff/logging that make it survivable
2. `fde/models.py` — what "valid" means
3. `fde/extraction.py` — how a document becomes a validated object
4. `fde/batch.py` — how ten sequential waits become one
5. `fde/cli.py` — the interface a teammate would actually use

All data in `documents/` is **synthetic**. No real personal information.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the [LICENSE](LICENSE) file.
