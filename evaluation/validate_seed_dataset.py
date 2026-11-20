"""Validate Sprint 0 fixtures offline, without claiming legal correctness.

Usage: python evaluation/validate_seed_dataset.py [path/to/dataset.json]
"""
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_PATH = Path(__file__).resolve().parent / 'datasets' / 'seed_tax_questions.json'


def validate(rows):
    errors = []
    if not isinstance(rows, list):
        return ['Dataset must be a JSON array.']
    if len(rows) != 30:
        errors.append(f'Expected 30 seed cases, got {len(rows)}.')
    ids, questions = set(), set()
    fields = {'id', 'tax_category', 'question', 'taxpayer_type', 'tax_period',
              'material_facts', 'is_clarification_needed', 'applicable_authority',
              'ground_truth_conclusion', 'jurisdiction', 'research_as_of',
              'review_status', 'expected_behavior', 'clarification_questions'}
    citation_fields = {'document_number', 'document_type', 'article', 'clause',
                       'point', 'title', 'source_url', 'version_note', 'last_checked_at'}
    for index, row in enumerate(rows):
        label = f'Row {index + 1}'
        if not isinstance(row, dict):
            errors.append(f'{label}: expected object.')
            continue
        label = row.get('id', label)
        missing = fields - row.keys()
        if missing:
            errors.append(f'{label}: missing {sorted(missing)}.')
            continue
        for key in fields - {'applicable_authority', 'clarification_questions', 'is_clarification_needed'}:
            if not isinstance(row[key], str) or not row[key].strip():
                errors.append(f'{label}: {key} must be nonempty text.')
        if not isinstance(row['id'], str) or not isinstance(row['question'], str):
            continue
        if row['id'] in ids or row['question'].strip().casefold() in questions:
            errors.append(f'{label}: duplicate ID or question.')
        ids.add(row['id'])
        questions.add(row['question'].strip().casefold())
        if row['tax_category'] not in {'VAT', 'CIT', 'PIT', 'EINVOICE'} or row['jurisdiction'] != 'VN':
            errors.append(f'{label}: invalid category or jurisdiction.')
        try:
            date.fromisoformat(row['research_as_of'])
        except (ValueError, TypeError):
            errors.append(f'{label}: invalid research_as_of date.')
        clarify = row['is_clarification_needed']
        if not isinstance(clarify, bool):
            errors.append(f'{label}: clarification flag must be boolean.')
        expected = 'clarify' if clarify else 'answer_with_citations'
        if row['expected_behavior'] != expected:
            errors.append(f'{label}: inconsistent expected behavior.')
        if row['review_status'] != 'pending_tax_expert_review':
            errors.append(f'{label}: Sprint 0 seed must retain pending expert review.')
        prompts = row['clarification_questions']
        if not isinstance(prompts, list) or any(not isinstance(q, str) or not q.strip() for q in prompts):
            errors.append(f'{label}: invalid clarification questions.')
        elif clarify and not prompts:
            errors.append(f'{label}: clarification case needs targeted questions.')
        authorities = row['applicable_authority']
        if not isinstance(authorities, list):
            errors.append(f'{label}: applicable_authority must be a list.')
            continue
        if not clarify and not authorities:
            errors.append(f'{label}: answerable case requires authority.')
        for a in authorities:
            if not isinstance(a, dict) or citation_fields - a.keys():
                errors.append(f'{label}: incomplete citation.')
                continue
            if any(not isinstance(a[k], str) for k in citation_fields):
                errors.append(f'{label}: citation fields must be text.')
                continue
            if not a['article'].startswith('Điều ') or (a['point'] and not a['clause']):
                errors.append(f'{label}: invalid citation hierarchy.')
            url = urlparse(a['source_url'])
            host = url.hostname or ''
            if url.scheme != 'https' or not any(host == d or host.endswith('.' + d) for d in ('chinhphu.vn', 'baochinhphu.vn', 'vbpl.vn', 'moj.gov.vn')):
                errors.append(f'{label}: expected official HTTPS source URL.')
            try:
                date.fromisoformat(a['last_checked_at'])
            except ValueError:
                errors.append(f'{label}: invalid last_checked_at date.')
            years = re.findall(r'/(\d{4})/', a['document_number'])
            if row['tax_period'] == '2024' and years and int(years[0]) > 2024:
                errors.append(f'{label}: later-issued authority in a 2024 case; review temporal applicability.')
    return errors


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH
    try:
        rows = json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1
    errors = validate(rows)
    if errors:
        print('\n'.join(f'FAIL: {e}' for e in errors), file=sys.stderr)
        return 1
    counts = Counter(r['tax_category'] for r in rows)
    clarify = sum(r['is_clarification_needed'] for r in rows)
    print(f'PASS: {len(rows)} cases; {len(rows)-clarify} answerable; {clarify} clarification; {dict(counts)}')
    print('Structural checks only. Expert legal review and live citation validation remain separate.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
