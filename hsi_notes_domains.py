#!/usr/bin/env python3
"""Explicit, deterministic, review-only semantic adapters for a locked Notes/ snapshot.

This program reads local UTF-8 documents, creates proposed inputs and governance
records, and optionally writes one JSON review artifact. It NEVER invokes renderers,
external services, broker APIs, or deployment programs.
"""
import argparse
import hashlib
import json
from pathlib import Path

from hsi_notes_review import audit

PROTOCOL = 'HSI-NOTES-DOMAIN-PLAN/0.1'
EXPECTED_SOURCES = 33
# Mapping is a declared editorial interpretation, not a mathematical deduction.
DOCUMENT_RULES = (
    ('Notes/1', 'prime', ('質數公式', 'Prime Formula'), ('prime', 'pulse', 'counterpoint')),
    ('Notes/2', 'analytic', ('解析延拓方程', 'Analytic Continuation Equation'), ('continuation', 'transition', 'legato')),
    ('Notes/3', 'correspondence', ('普遍對應原理', 'Universal Correspondence Principle'), ('correspondence', 'call and response')),
    ('Notes/4', 'bitwise', ('HSI 位元後設理論', 'HSI Bitwise Metatheory'), ('binary', 'rhythm')),
)
DOMAINS = ('music_corpus', 'music_native', 'music_ai_bridge', 'utm', 'trader_42', 'omega')


class ReviewError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def make_plan(root, lock):
    root = Path(root)
    inventory = audit(root, lock)
    if inventory['inventory_status'] != 'SOURCE_INVENTORY_VERIFIED':
        raise ReviewError('locked Notes inventory failed: ' + json.dumps(inventory['issues'], ensure_ascii=False))
    if inventory['expected_count'] != EXPECTED_SOURCES or inventory['observed_count'] != EXPECTED_SOURCES:
        raise ReviewError(f'expected exactly {EXPECTED_SOURCES} locked source files')
    if not isinstance(lock.get('source_commit'), str) or len(lock['source_commit']) != 40:
        raise ReviewError('missing pinned source commit')
    evidence = []
    for path, code, required, keywords in DOCUMENT_RULES:
        p = root / path
        try:
            # Documents are bounded by the locked inventory (largest is ~65 KB).
            text = p.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError) as e:
            raise ReviewError('unreadable UTF-8 source: ' + path) from e
        heading = text[:1300]
        if not all(marker in heading for marker in required):
            raise ReviewError('document heading does not match declared rule: ' + path)
        evidence.append({
            'concept_id': code,
            'path': path,
            'sha256': inventory['observed'][path]['sha256'],
            'required_heading_markers': list(required),
            'candidate_musical_terms': list(keywords),
            'interpretation': 'HUMAN_CURATED_ANALOGY_NOT_PROVEN_EQUIVALENCE'
        })
    files = [
        {'path': path, 'sha256': observed['sha256'],
         'role': 'concept_source' if path in {rule[0] for rule in DOCUMENT_RULES} else 'reference_and_audit_source'}
        for path, observed in sorted(inventory['observed'].items())
    ]
    fingerprint = hashlib.sha256(canonical(files)).hexdigest()
    keywords = [term for item in evidence for term in item['candidate_musical_terms']]
    theme = ' '.join(keywords)
    # UTM word is an explicitly bounded digest prefix. This encodes the inventory
    # fingerprint, NOT the content or meaning of mathematical documents.
    word = ''.join(f'{b:08b}' for b in bytes.fromhex(fingerprint[:8]))
    plans = {
        'music_corpus': {
            'status': 'PROPOSAL_ONLY', 'input_kind': 'optional_search_keywords',
            'candidate_keywords': theme, 'external_search_performed': False,
            'audio_generated': False, 'rights_verified': False,
            'review_gate': 'VERIFY_SOURCE_LICENSE_AND_WAV_BEFORE_USE'
        },
        'music_native': {
            'status': 'PROPOSAL_ONLY', 'input_kind': 'local_keyword_prompt',
            'candidate_keywords': theme, 'renderer_invoked': False,
            'audio_generated': False, 'review_gate': 'HUMAN_APPROVAL_OF_CREATIVE_MAPPING'
        },
        'music_ai_bridge': {
            'status': 'DISABLED_PENDING_EXPLICIT_AUTHORIZATION',
            'input_kind': 'draft_only', 'candidate_keywords': theme,
            'external_api_calls': 0, 'paid_generation_authorized': False,
            'review_gate': 'SEPARATE_AUTHORIZATION_AND_COST_REVIEW'
        },
        'utm': {
            'status': 'PROPOSAL_ONLY', 'input_kind': 'finite_bit_word_from_manifest_hash',
            'finite_word': word, 'max_steps': 32, 'simulator_invoked': False,
            'interpretation': 'digest-derived demonstration input, not a formal proof',
            'review_gate': 'REVIEW_MACHINE_AND_INVARIANTS'
        },
        'trader_42': {
            'status': 'READ_ONLY_REVIEW', 'input_kind': 'source_provenance_record',
            'document_manifest_sha256': fingerprint,
            'mode': 'PAPER_ONLY', 'broker_calls': 0, 'orders': 0,
            'live_trading_authorized': False,
            'review_gate': 'SEPARATE_HUMAN_REVIEW_NO_REAL_ORDERS'
        },
        'omega': {
            'status': 'HUMAN_GOVERNANCE_REVIEW', 'input_kind': 'revisability_checklist',
            'document_manifest_sha256': fingerprint,
            'epistemic_fallibility_acknowledged': True,
            'human_override_required': True,
            'ethical_truth_proven': False,
            'review_gate': 'HUMAN_ASSESSES_NORMATIVE_ASSUMPTIONS'
        }
    }
    result = {
        'protocol': PROTOCOL,
        'source_repo': lock['source_repo'],
        'source_commit': lock['source_commit'],
        'source_inventory': 'SOURCE_INVENTORY_VERIFIED',
        'source_count': len(files),
        'documents': evidence,
        'manifest_sha256': fingerprint,
        'all_source_files': files,
        'domain_plans': plans,
        'domain_gates': {d: 'NOT_EXECUTED_NOT_DEPLOYED' for d in DOMAINS},
        'claims': {'generated_audio': False, 'remote_deployment': False,
                   'executed_orders': False, 'proved_philosophical_or_mathematical_truth': False},
        'plan_status': 'READY_FOR_HUMAN_REVIEW_NOT_DEPLOYED'
    }
    result['plan_uid'] = hashlib.sha256(canonical(result)).hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default=str(Path(__file__).resolve().parent))
    parser.add_argument('--lock', default=str(Path(__file__).with_name('hsi_notes_review.lock.json')))
    parser.add_argument('--out', help='Optional path for one JSON review artifact; otherwise stdout')
    args = parser.parse_args()
    try:
        lock = json.loads(Path(args.lock).read_text(encoding='utf-8'))
        result = make_plan(args.root, lock)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, 'REVIEW_REQUIRED: ' + str(exc) + '\n')
    content = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + '\n'
    if args.out:
        Path(args.out).write_text(content, encoding='utf-8')
    else:
        print(content, end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
