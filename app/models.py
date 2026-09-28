from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Fact(StrictModel):
    label: str = Field(min_length=1, max_length=200)
    any_of: list[str] = Field(min_length=1, max_length=12)

    @model_validator(mode='after')
    def nonempty_aliases(self):
        if any(not x.strip() for x in self.any_of):
            raise ValueError('Fact aliases cannot be blank')
        return self


class Case(StrictModel):
    id: str = Field(pattern=r'^[a-z0-9-]{1,40}$')
    category: str = Field(min_length=1, max_length=60)
    question: str = Field(min_length=10, max_length=4000)
    facts: list[Fact] = Field(min_length=1, max_length=10)
    require_code: bool = False
    min_words: int = Field(default=15, ge=1, le=500)
    review_notes: str = Field(min_length=1, max_length=2000)


class Dataset(StrictModel):
    version: str = Field(min_length=1, max_length=60)
    cases: list[Case] = Field(min_length=1, max_length=500)

    @model_validator(mode='after')
    def unique_ids(self):
        ids = [c.id for c in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError('Dataset case IDs must be unique')
        return self


class Version(StrictModel):
    id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,60}$')
    provider: Literal['demo', 'ollama', 'devara']
    model: str = Field(min_length=1, max_length=120)
    system_prompt: str = Field(min_length=1, max_length=8000)
    temperature: float = Field(default=0, ge=0, le=2)
    seed: int = Field(default=42, ge=0, le=2147483647)
    demo_variant: Literal['baseline', 'candidate'] = 'baseline'


class RunRequest(StrictModel):
    version_id: str = Field(min_length=1, max_length=60)
    timeout_seconds: float = Field(default=30, ge=0.01, le=120)


class Review(StrictModel):
    reviewer: str = Field(min_length=1, max_length=100)
    correctness: int = Field(ge=0, le=2)
    completeness: int = Field(ge=0, le=2)
    clarity: int = Field(ge=0, le=2)
    notes: str = Field(min_length=1, max_length=3000)
