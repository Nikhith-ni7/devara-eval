import json
import pytest
from pydantic import ValidationError
from app.models import Dataset, Fact
from app.providers import ROOT
from app.scoring import contains_phrase, score_answer


def test_fixture_corpus_satisfies_declared_checks(dataset):
    answers = json.loads((ROOT / 'data/demo_answers.json').read_text())
    assert len(dataset.cases) == 50
    assert set(answers) == {c.id for c in dataset.cases}
    for case in dataset.cases:
        result = score_answer(case, answers[case.id])
        assert result['passed'], (case.id, result)


@pytest.mark.parametrize('text,phrase,expected', [('BLACKLIST','list',False),('A list.','list',True),('IMMUTABLE','mutable',False),('O(log n)','O(log n)',True),('dependency\n injection','dependency injection',True),('Tuple is IMMUTABLE','immutable',True)])
def test_literal_boundaries(text, phrase, expected):
    assert contains_phrase(text, phrase) is expected


def test_empty_answer_fails(dataset):
    result = score_answer(dataset.cases[0], ' ')
    assert result['score'] == 0
    assert not result['passed']


def test_code_fence_must_close(dataset):
    case = dataset.cases[1]
    answer = ' '.join(['definition None'] * 20) + '\n```python\nx=1'
    assert not score_answer(case, answer)['passed']
    assert score_answer(case, answer + '\n```')['passed']


def test_lexical_limitation_is_explicit(dataset):
    # This deliberately incorrect answer passes lexical checks. Human review is required.
    answer = 'Lists are not mutable and tuples are not immutable. This wrong explanation still repeats the expected words enough times.'
    assert score_answer(dataset.cases[0], answer)['passed']


def test_duplicate_dataset_ids_rejected(dataset):
    data = dataset.model_dump()
    data['cases'].append(data['cases'][0])
    with pytest.raises(ValidationError):
        Dataset.model_validate(data)


def test_blank_alias_rejected():
    with pytest.raises(ValidationError):
        Fact(label='test', any_of=[' '])
