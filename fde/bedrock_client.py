"""First Bedrock call — invoke Claude via the Converse API."""

import logging
from typing import TYPE_CHECKING, Protocol, cast

import boto3
from botocore.exceptions import ClientError
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

if TYPE_CHECKING:
    from mypy_boto3_bedrock_runtime import BedrockRuntimeClient
    from tenacity import RetryCallState

MODEL_ID = "us.anthropic.claude-sonnet-5"
logger = logging.getLogger(__name__)


class BedrockResponseError(Exception):
    """The Bedrock response wasn't shaped the way we expected.

    Raised instead of leaking a low-level KeyError/IndexError so callers get a
    diagnosable, domain-level error with the offending payload attached.
    """

    def __init__(self, message: str, raw: object = None) -> None:
        super().__init__(message)
        self.raw = raw


class LLMClient(Protocol):
    """The shape of a Bedrock client, as far as our code depends on it.

    Any object with a matching ``converse`` method satisfies this - the real
    boto3 client and our test fakes alike, without inheriting from it.
    """

    def converse(
        self,
        *,
        modelId: str,
        messages: list[dict[str, object]],
        toolConfig: dict[str, object] | None = None,
    ) -> dict[str, object]: ...


def _is_throttling(exc: BaseException) -> bool:
    """True if the exception is a transient throttling error worth retrying."""
    if isinstance(exc, ClientError):
        code = exc.response.get("Error", {}).get("Code")
        return code in ("ThrottlingException", "TooManyRequestsException")
    return False


def _log_retry(retry_state: "RetryCallState") -> None:
    if retry_state.next_action is None:
        return
    logger.warning(
        "Bedrock call throttled; retrying (attempt %d, sleeping %.1fs)",
        retry_state.attempt_number,
        retry_state.next_action.sleep,
    )


@retry(
    retry=retry_if_exception(_is_throttling),
    wait=wait_exponential_jitter(initial=1, max=30),
    stop=stop_after_attempt(4),
    reraise=True,
    before_sleep=_log_retry,
)
def _converse_with_retry(client: LLMClient, **kwargs: object) -> dict[str, object]:
    """Call converse, retrying only on transient throttling errors."""
    return client.converse(**kwargs)  # type: ignore[arg-type]


def _text_from(response: dict[str, object]) -> str:
    """Pull the assistant's text out of a Converse response, or raise clearly.

    Walks output -> message -> content[0] -> text. Any shape surprise
    (throttled/error response, API change, tool-only reply) is caught and
    re-raised as a diagnosable BedrockResponseError instead of a cryptic
    KeyError/IndexError/TypeError leaking from deep in the dict.
    """
    try:
        output = cast(dict[str, object], response["output"])
        message = cast(dict[str, object], output["message"])
        content = cast(list[dict[str, object]], message["content"])
        return cast(str, content[0]["text"])
    except (KeyError, IndexError, TypeError) as e:
        raise BedrockResponseError(
            f"unexpected Converse response shape: {e}", raw=response
        ) from e


def get_client() -> "BedrockRuntimeClient":
    """Return a Bedrock *runtime* client (the data plane — for invoking models)."""
    return boto3.client("bedrock-runtime")


def ask(prompt: str) -> str:
    client = get_client()
    response = _converse_with_retry(
        cast(LLMClient, client),
        modelId=MODEL_ID,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
    )
    return _text_from(response)
