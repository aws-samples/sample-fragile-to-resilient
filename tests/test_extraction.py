from collections.abc import Mapping

import pytest

from fde.extraction import ExtractionError, extract_policy


def fake_converse_response(args: Mapping[str, object]) -> dict[str, object]:
    """Build a Converse response dict whose toolUse.input is `args`."""
    return {
        "output": {
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "toolUse": {
                            "toolUseId": "tool-1",
                            "name": "extract_policy",
                            "input": args,
                        }
                    }
                ],
            }
        }
    }


class FakeClient:
    """A stand-in Bedrock client whose .converse returns scripted responses in order."""

    def __init__(self, responses: list[dict[str, object]]) -> None:
        self._responses = responses
        self.call_count = 0

    def converse(self, **kwargs: object) -> dict[str, object]:
        response = self._responses[self.call_count]
        self.call_count += 1
        return response


def test_extract_policy_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    valid_args = {
        "policy_id": "POL-1",
        "insured": {"name": "Dana Okafor", "age": 41, "email": "dana@example.com"},
        "coverages": [
            {
                "type": "general_liability",
                "limits": {"per_occurrence": 1_000_000, "aggregate": 2_000_000},
            }
        ],
    }
    fake = FakeClient([fake_converse_response(valid_args)])
    monkeypatch.setattr("fde.extraction.get_client", lambda: fake)

    result = extract_policy("some document text")

    assert result.policy_id == "POL-1"
    assert result.insured.age == 41
    assert fake.call_count == 1


def test_extract_policy_repairs_after_bad_age(monkeypatch: pytest.MonkeyPatch) -> None:
    bad_args = {
        "policy_id": "POL-1",
        "insured": {"name": "Dana Okafor", "age": 180, "email": "dana@example.com"},
        "coverages": [
            {
                "type": "general_liability",
                "limits": {"per_occurrence": 1_000_000, "aggregate": 2_000_000},
            }
        ],
    }
    good_args = {
        "policy_id": "POL-1",
        "insured": {"name": "Dana Okafor", "age": 41, "email": "dana@example.com"},
        "coverages": [
            {
                "type": "general_liability",
                "limits": {"per_occurrence": 1_000_000, "aggregate": 2_000_000},
            }
        ],
    }

    fake = FakeClient(
        [fake_converse_response(bad_args), fake_converse_response(good_args)]
    )
    monkeypatch.setattr("fde.extraction.get_client", lambda: fake)

    result = extract_policy("some document text")

    assert result.insured.age == 41
    assert fake.call_count == 2


def test_extract_policy_raises_after_exhausting_repairs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bad_args = {
        "policy_id": "POL-1",
        "insured": {"name": "Dana Okafor", "age": 180, "email": "dana@example.com"},
        "coverages": [
            {
                "type": "general_liability",
                "limits": {"per_occurrence": 1_000_000, "aggregate": 2_000_000},
            }
        ],
    }
    bad = fake_converse_response(bad_args)
    fake = FakeClient([bad, bad, bad])
    monkeypatch.setattr("fde.extraction.get_client", lambda: fake)

    with pytest.raises(ExtractionError) as exc_info:
        extract_policy("some document text")

    assert exc_info.value.attempts == 3
    assert fake.call_count == 3
    assert exc_info.value.validation_errors


def test_extract_policy_raises_on_malformed_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bad_response: dict[str, object] = {
        "output": {
            "message": {
                "content": [{"text": "I could not extract anything."}],
            }
        }
    }
    fake = FakeClient([bad_response])
    monkeypatch.setattr("fde.extraction.get_client", lambda: fake)
    with pytest.raises(ExtractionError) as exc_info:
        extract_policy("some text")
    assert fake.call_count == 1
    assert exc_info.value.last_raw is not None
