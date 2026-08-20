from typing import TYPE_CHECKING

from pydantic import ValidationError

from .bedrock_client import MODEL_ID, get_client
from .models import PolicySubmission

if TYPE_CHECKING:
    from mypy_boto3_bedrock_runtime.type_defs import (
        MessageUnionTypeDef,
        ToolConfigurationTypeDef,
    )
    from pydantic_core import ErrorDetails


class ExtractionError(Exception):
    """Raised when the model can't produce a valid PolicySubmission.

    Carries the debug payload as *attributes* (machine-readable), not just
    a message string, so callers can log/branch on the details.
    """

    def __init__(
        self,
        message: str,
        attempts: int,
        validation_errors: "list[ErrorDetails] | None" = None,
        last_raw: str | None = None,
    ) -> None:
        super().__init__(message)
        self.attempts = attempts
        self.validation_errors = validation_errors
        self.last_raw = last_raw


def extract_policy(document: str, max_repairs: int = 2) -> PolicySubmission:
    """Extract a validated PolicySubmission, or raise ExtractionError on failure."""
    tool_config: ToolConfigurationTypeDef = {
        "tools": [
            {
                "toolSpec": {
                    "name": "extract_policy",
                    "description": "Extract structured policy data from the document",
                    "inputSchema": {"json": PolicySubmission.model_json_schema()},
                }
            },
        ],
        "toolChoice": {"tool": {"name": "extract_policy"}},
    }

    client = get_client()
    messages: list[MessageUnionTypeDef] = [
        {"role": "user", "content": [{"text": document}]}
    ]

    last_errors: list[ErrorDetails] = []
    last_args: object = None
    for _ in range(1 + max_repairs):
        response = client.converse(
            modelId=MODEL_ID,
            messages=messages,
            toolConfig=tool_config,
        )
        try:
            content = response["output"]["message"]["content"]
            tool_use = next(block["toolUse"] for block in content if "toolUse" in block)
            args = tool_use["input"]
            last_args = args
        except (KeyError, IndexError, TypeError, StopIteration) as e:
            raise ExtractionError(
                f"unexpected Converse response shape: {e}",
                attempts=1 + max_repairs,
                last_raw=str(response),
            ) from e

        try:
            return PolicySubmission.model_validate(args)
        except ValidationError as e:
            last_errors = e.errors()
            messages.append(response["output"]["message"])
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "toolResult": {
                                "toolUseId": tool_use["toolUseId"],
                                "content": [
                                    {"text": f"Validation failed: {e.errors()}"}
                                ],
                                "status": "error",
                            }
                        }
                    ],
                }
            )

    raise ExtractionError(
        f"Failed to extract valid PolicySubmission after {1 + max_repairs} attempts",
        attempts=1 + max_repairs,
        validation_errors=last_errors,
        last_raw=str(last_args),
    )
