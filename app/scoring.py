"""Explainable lexical checks. These do NOT establish semantic correctness."""
import re
import unicodedata
from .models import Case

SCORER_VERSION = 'lexical-v1'


def normalize(text: str) -> str:
    return ' '.join(unicodedata.normalize('NFKC', text).casefold().split())


def contains_phrase(text: str, phrase: str) -> bool:
    # Literal aliases, word boundaries: 'list' must not match 'blacklist'.
    return re.search(r'(?<!\w)' + re.escape(normalize(phrase)) + r'(?!\w)', normalize(text)) is not None


def score_answer(case: Case, answer: str) -> dict:
    checks = [{'name': 'nonempty', 'passed': bool(answer.strip())}]
    checks += [{'name': f'fact: {fact.label}', 'passed': any(contains_phrase(answer, a) for a in fact.any_of)} for fact in case.facts]
    checks.append({'name': f'minimum {case.min_words} words', 'passed': len(answer.split()) >= case.min_words})
    if case.require_code:
        checks.append({'name': 'fenced code block', 'passed': bool(re.search(r'```[^\n]*\n\s*\S[\s\S]*?\n```', answer))})
    return {'checks': checks, 'score': round(sum(c['passed'] for c in checks) / len(checks), 4),
            'passed': all(c['passed'] for c in checks)}
