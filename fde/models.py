from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    StrictStr,
    field_validator,
    model_validator,
)


class Insured(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    age: int
    email: EmailStr

    @field_validator("age")
    @classmethod
    def age_must_be_realistic(cls, v: int) -> int:
        if v < 0 or v > 120:
            raise ValueError("age must be a realistic human age")
        return v


class Limits(BaseModel):
    model_config = ConfigDict(extra="forbid")

    per_occurrence: int
    aggregate: int

    @model_validator(mode="after")
    def aggregate_must_cover_occurrence(self) -> "Limits":
        if self.aggregate < self.per_occurrence:
            raise ValueError("aggregate cannot be less than per_occurrence")
        return self


class Coverage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    limits: Limits


class PolicySubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_id: StrictStr
    insured: Insured
    coverages: list[Coverage]
