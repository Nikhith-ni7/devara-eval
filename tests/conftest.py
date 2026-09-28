import json
from pathlib import Path
import pytest
from app.models import Dataset, Version
from app.store import Store

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def dataset():
    return Dataset.model_validate_json((ROOT / 'data/programming-v1.json').read_text())


@pytest.fixture
def versions():
    return {v['id']: Version.model_validate(v).model_dump() for v in json.loads((ROOT / 'prompts/versions.json').read_text())}


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / 'test.sqlite3')
