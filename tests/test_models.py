import pytest
from pydantic import ValidationError

from fde.models import Coverage, Insured, Limits, PolicySubmission


def test_valid_insured_builds() -> None:
    person = Insured(name="Ada Lovelace", age=36, email="ada@example.com")
    assert person.age == 36


def test_negative_age_is_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Insured(name="Bad Age", age=-5, email="x@example.com")
    assert "age must be a realistic human age" in str(exc_info.value)


@pytest.mark.parametrize("age", [0, 120, 36])
def test_valid_ages_accepted(age: int) -> None:
    person = Insured(name="Ada Lovelace", age=age, email="ada@example.com")
    assert person.age == age


@pytest.mark.parametrize("age", [-1, 121, -100, 200])
def test_invalid_ages_rejected(age: int) -> None:
    with pytest.raises(ValidationError) as exc_info:
        Insured(name="Bad Age", age=age, email="x@example.com")
    assert "age must be a realistic human age" in str(exc_info.value)


@pytest.mark.parametrize("email", ["plainaddress", "no-at-sign", ""])
def test_emails_without_at_are_rejected(email: str) -> None:
    with pytest.raises(ValidationError) as exc_info:
        Insured(name="Edge", age=30, email=email)
    errors = exc_info.value.errors()
    assert errors[0]["loc"] == ("email",)


def test_aggregate_below_occurence_is_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Limits(per_occurrence=1_000_000, aggregate=500_000)
    assert "aggregate cannot be less than per_occurrence" in str(exc_info.value)


def test_non_string_policy_id_is_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        PolicySubmission(
            policy_id=12345,  # type: ignore[arg-type]  # intentional int → tests strict rejection
            insured=Insured(name="Ada Lovelace", age=36, email="ada@example.com"),
            coverages=[
                Coverage(
                    type="general_liability",
                    limits=Limits(per_occurrence=1_000_000, aggregate=2_000_000),
                )
            ],
        )
    errors = exc_info.value.errors()
    assert errors[0]["loc"] == ("policy_id",)


@pytest.fixture
def valid_submission() -> PolicySubmission:
    return PolicySubmission(
        policy_id="POL-001",
        insured=Insured(name="Ada Lovelace", age=36, email="ada@example.com"),
        coverages=[
            Coverage(
                type="general_liability",
                limits=Limits(per_occurrence=1_000_000, aggregate=2_000_000),
            )
        ],
    )


def test_valid_submission_builds(valid_submission: PolicySubmission) -> None:
    assert valid_submission.policy_id == "POL-001"
    assert valid_submission.coverages[0].limits.aggregate == 2_000_000


def test_bad_limits_nested_deep_is_caught() -> None:
    with pytest.raises(ValidationError) as exc_info:
        PolicySubmission(
            policy_id="POL-002",
            insured={"name": "Ada", "age": 36, "email": "ada@example.com"},  # type: ignore[arg-type]  # intentional dict → tests pydantic coercion
            coverages=[
                {
                    "type": "general_liability",  # type: ignore[list-item]  # intentional dict → tests pydantic coercion
                    "limits": {"per_occurrence": 1_000_000, "aggregate": 500_000},
                },
            ],
        )
    errors = exc_info.value.errors()
    assert errors[0]["loc"] == ("coverages", 0, "limits")
