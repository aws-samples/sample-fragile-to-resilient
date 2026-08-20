import logging

import pytest
from botocore.exceptions import ClientError

from fde.bedrock_client import _converse_with_retry


def make_throttling_error() -> ClientError:
    """Build a ClientError that looks like a Bedrock throttling response."""
    return ClientError(
        error_response={
            "Error": {"Code": "ThrottlingException", "Message": "slow down"}
        },
        operation_name="Converse",
    )


class ThrottlingClient:
    """Fake client: raises ThrottlingException `fail_times`, then returns a response."""

    def __init__(self, fail_times: int) -> None:
        self.fail_times = fail_times
        self.call_count = 0

    def converse(self, **kwargs: object) -> dict[str, object]:
        self.call_count += 1
        if self.call_count <= self.fail_times:
            raise make_throttling_error()
        return {"output": "ok"}


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make tenacity's backoff instant so retry tests don't actually wait."""
    monkeypatch.setattr("tenacity.nap.time.sleep", lambda _: None)


def test_retries_then_succeeds_on_throttling() -> None:
    client = ThrottlingClient(fail_times=2)

    result = _converse_with_retry(client, modelId="m", messages=[])

    assert result == {"output": "ok"}
    assert client.call_count == 3


def test_logs_a_warning_on_each_retry(caplog: pytest.LogCaptureFixture) -> None:
    client = ThrottlingClient(fail_times=2)
    with caplog.at_level(logging.WARNING):
        _converse_with_retry(client, modelId="m", messages=[])
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 2
    assert "throttled" in warnings[0].message
