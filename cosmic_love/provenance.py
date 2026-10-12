#!/usr/bin/env python3
"""Offline proof-scope source receipts and review-only logic change proposals.

Never fetches conversations or network content. All records are LOCAL-ONLY and
fail closed. Integrity != truth, authentic consent, or universal completeness.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sys

PROTOCOL = 'HSI-COSMIC-LOVE-PROVENANCE/1.0'
CONSENT = 'HSI-COSMIC-LOVE-CONSENT/1.0'
ZERO = '0' * 64
MAX_SOURCE_BYTES = 8 * 1024 * 1024
MAX_LEDGER_BYTES = 2 * 1024 * 1024
ALLOWED_TYPES = {'CHAT_EXPORT', 'RESEARCH_DOCUMENT', 'GITHUB_SNAPSHOT', 'DEPLOYMENT_RECEIPT'}
HEX = re.compile(r'[0-9a-f]{64}\Z')

def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def validate_digest(value):
    if type(value) is not str or not HEX.fullmatch(value):
        raise ValueError('expected exact lowercase SHA-256')
    return value

def regular_bytes(path, limit):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('source must be a regular non-symlink file')
    if path.stat().st_size > limit:
        raise ValueError('file too large')
    with path.open('rb') as f:
        raw = f.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('file too large')
    return raw

def validate_payload(kind, payload):
    if type(payload) is not dict:
        raise ValueError('invalid payload')
    if kind == 'SOURCE_OBSERVATION':
        keys = {'source_sha256','consent_sha256','byte_length','source_type',
                'purpose','source_retained','authorization','truth_status'}
        if set(payload) != keys:
            raise ValueError('invalid source receipt schema')
        validate_digest(payload['source_sha256'])
        validate_digest(payload['consent_sha256'])
        if type(payload['byte_length']) is not int or not 0 <= payload['byte_length'] <= MAX_SOURCE_BYTES:
            raise ValueError('invalid source length')
        if type(payload['source_type']) is not str or payload['source_type'] not in ALLOWED_TYPES or payload['purpose'] != 'FINITE_RESEARCH_REVIEW':
            raise ValueError('source outside allowed purpose')
        if payload['source_retained'] is not False or payload['authorization'] != 'DECLARED_NOT_CRYPTOGRAPHICALLY_AUTHENTICATED':
            raise ValueError('source retention or authorization claim defect')
        if payload['truth_status'] != 'OBSERVED_NOT_PROVEN':
            raise ValueError('source truth status defect')
    elif kind == 'LOGIC_CHANGE_PROPOSAL':
        keys = {'old_logic_sha256','new_logic_sha256','counterexample_sha256',
                'rationale_sha256','status','enacted','auto_deploy','live_trading'}
        if set(payload) != keys:
            raise ValueError('invalid logic proposal schema')
        for k in ('old_logic_sha256','new_logic_sha256','counterexample_sha256','rationale_sha256'):
            validate_digest(payload[k])
        if payload['old_logic_sha256'] == payload['new_logic_sha256']:
            raise ValueError('logic versions identical')
        if (payload['status'],payload['enacted'],payload['auto_deploy'],payload['live_trading']) != ('REVIEW_REQUIRED',False,False,False):
            raise ValueError('unsafe or unsupported proposal status')
    else:
        raise ValueError('unsupported event type')

def verify(rows):
    if type(rows) is not list or len(rows)>2048:
        raise ValueError('invalid event list')
    prev=ZERO
    for idx,row in enumerate(rows):
        if type(row) is not dict or set(row) != {'protocol','index','previous','kind','payload','digest'}:
            raise ValueError('event schema defect')
        if row['protocol']!=PROTOCOL or type(row['index']) is not int or row['index']!=idx or row['previous']!=prev:
            raise ValueError('broken event sequence')
        validate_payload(row['kind'],row['payload'])
        expected=digest(canonical({k:v for k,v in row.items() if k != 'digest'}))
        if row['digest']!=expected:
            raise ValueError('broken event hash')
        prev=expected
    return {'protocol':PROTOCOL,'status':'STRUCTURAL_CHAIN_VERIFIED',
            'events':len(rows),'tip_sha256':prev,'source_truth_proven':False,
            'user_consent_identity_authenticated':False,
            'externally_anchored':False,'logic_updates_enacted':False,
            'trading_enabled':False}

def parse_journal(raw):
    if len(raw)>MAX_LEDGER_BYTES:
        raise ValueError('journal limit exceeded')
    if raw and not raw.endswith(b'\n'):
        raise ValueError('partial final journal entry')
    rows=[json.loads(line) for line in raw.splitlines()]
    verify(rows)
    return rows

def append(path, kind, payload):
    path=Path(path)
    validate_payload(kind,payload)
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.is_symlink():
        raise ValueError('symlink journal denied')
    fd=os.open(path, os.O_RDWR | os.O_CREAT | getattr(os,'O_NOFOLLOW',0), 0o600)
    with os.fdopen(fd,'r+b') as f:
        fcntl.flock(f.fileno(),fcntl.LOCK_EX)
        try:
            f.seek(0)
            rows=parse_journal(f.read(MAX_LEDGER_BYTES+1))
            event={'protocol':PROTOCOL,'index':len(rows),
                   'previous':rows[-1]['digest'] if rows else ZERO,
                   'kind':kind,'payload':payload}
            event['digest']=digest(canonical(event))
            line=canonical(event)+b'\n'
            if f.tell()+len(line)>MAX_LEDGER_BYTES:
                raise ValueError('journal limit exceeded')
            verify(rows+[event])
            f.seek(0,os.SEEK_END)
            f.write(line)
            f.flush();os.fsync(f.fileno())
            return event
        finally:
            fcntl.flock(f.fileno(),fcntl.LOCK_UN)

def observe(source, consent_file, journal):
    source=Path(source);consent_file=Path(consent_file)
    if source.resolve()==consent_file.resolve() or source.resolve()==Path(journal).resolve():
        raise ValueError('source path overlaps with consent or journal')
    raw=regular_bytes(source,MAX_SOURCE_BYTES)
    consent_raw=regular_bytes(consent_file,16*1024)
    c=json.loads(consent_raw)
    required={'protocol','source_sha256','source_type','purpose','granted','raw_retention'}
    if type(c) is not dict or set(c)!=required or c.get('protocol')!=CONSENT:
        raise ValueError('invalid consent declaration')
    validate_digest(c['source_sha256'])
    if c['source_sha256']!=digest(raw) or type(c['source_type']) is not str or c['source_type'] not in ALLOWED_TYPES:
        raise ValueError('unmatched source digest or type')
    if c['granted'] is not True or c['purpose']!='FINITE_RESEARCH_REVIEW' or c['raw_retention']!='NONE':
        raise ValueError('authorization absent or wrong scope')
    payload={'source_sha256':digest(raw),'consent_sha256':digest(canonical(c)),
             'byte_length':len(raw),'source_type':c['source_type'],
             'purpose':c['purpose'],'source_retained':False,
             'authorization':'DECLARED_NOT_CRYPTOGRAPHICALLY_AUTHENTICATED',
             'truth_status':'OBSERVED_NOT_PROVEN'}
    return append(journal,'SOURCE_OBSERVATION',payload)

def propose(journal, old, new, counterexample, rationale):
    b=regular_bytes(Path(rationale),64*1024)
    if not b.strip():
        raise ValueError('missing rationale')
    payload={'old_logic_sha256':validate_digest(old),
             'new_logic_sha256':validate_digest(new),
             'counterexample_sha256':validate_digest(counterexample),
             'rationale_sha256':digest(b),
             'status':'REVIEW_REQUIRED', 'enacted':False,
             'auto_deploy':False, 'live_trading':False}
    return append(journal,'LOGIC_CHANGE_PROPOSAL',payload)

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='mode',required=True)
    obs=sub.add_parser('observe');obs.add_argument('--source',required=True)
    obs.add_argument('--consent-file',required=True);obs.add_argument('--journal',required=True)
    prop=sub.add_parser('propose');prop.add_argument('--journal',required=True)
    for name in ('old','new','counterexample'):
        prop.add_argument('--'+name,required=True)
    prop.add_argument('--rationale',required=True)
    ck=sub.add_parser('check');ck.add_argument('--journal',required=True)
    args=p.parse_args(argv)
    try:
        if args.mode=='observe':
            result=observe(args.source,args.consent_file,args.journal)
        elif args.mode=='propose':
            result=propose(args.journal,args.old,args.new,args.counterexample,args.rationale)
        else:
            raw=regular_bytes(args.journal,MAX_LEDGER_BYTES) if Path(args.journal).exists() else b''
            result=verify(parse_journal(raw))
        print(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2))
    except (ValueError,OSError,UnicodeError,json.JSONDecodeError) as e:
        print('HOLD:',type(e).__name__,file=sys.stderr)
        return 2
    return 0
if __name__=='__main__':sys.exit(main())
