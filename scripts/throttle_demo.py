"""Demo: induce throttling and watch the retry logic survive it.

Scenario 1 (recover): a fake client raises ThrottlingException twice, then
answers. Routed through _converse_with_retry, the log shows one warning per
retry (with the backoff sleep it chose), then success.

Scenario 2 (give up): a client that throttles forever exhausts the 4-attempt
budget; reraise=True hands the caller the real ClientError, not a tenacity
wrapper. No AWS calls in either scenario — free.

Run:  python scripts/throttle_demo.py
"""

import logging
import time

from botocore.exceptions import ClientError

from fde.bedrock_client import _converse_with_retry

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")


class ThrottlingClient:
    """Fake client: raises ThrottlingException `fail_times`, then returns a response."""

    def __init__(self, fail_times: int) -> None:
        self.fail_times = fail_times
        self.call_count = 0

    def converse(self, **kwargs: object) -> dict[str, object]:
        self.call_count += 1
        if self.call_count <= self.fail_times:
            raise ClientError(
                error_response={
                    "Error": {"Code": "ThrottlingException", "Message": "slow down"}
                },
                operation_name="Converse",
            )
        return {"output": f"ok — answered on attempt {self.call_count}"}


if __name__ == "__main__":
    print("--- scenario 1: throttled twice, then recovers ---")
    client = ThrottlingClient(fail_times=2)
    start = time.perf_counter()
    result = _converse_with_retry(client, modelId="demo", messages=[])
    elapsed = time.perf_counter() - start
    print(f"result:  {result}")
    print(f"calls:   {client.call_count}")
    print(f"elapsed: {elapsed:.1f}s (the backoff waits, made visible)")

    print("\n--- scenario 2: throttled forever, retry budget exhausted ---")
    hopeless = ThrottlingClient(fail_times=99)
    try:
        _converse_with_retry(hopeless, modelId="demo", messages=[])
    except ClientError as e:
        code = e.response["Error"]["Code"]
        print(f"gave up after {hopeless.call_count} calls; caller sees the real {code}")
