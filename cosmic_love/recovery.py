#!/usr/bin/env python3
"""Offline Ed25519-signed proof journal snapshots, detached anchors and restoration.

No provider I/O. No secrets inside snapshot/anchor. A detached anchor needs
out-of-band publication and a separately trusted public key to resist rollback.
Signed statements attest to byte integrity and the specifically named finite
validator's outcome; they do not attest to universal mathematical truth.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

from cosmic_love import closure_worker as worker
from cosmic_love import provenance as source

FORMAT = 'COSMIC-LOVE-RECOVERY/1'
ANCHOR_FORMAT = 'COSMIC-LOVE-DETACHED-ANCHOR/1'
MAX_SNAPSHOT_BYTES = 5 * 1024 * 1024
MAX_LEDGER_BYTES = {'worker': 1024 * 1024, 'source': source.MAX_LEDGER_BYTES}


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def b64(b):
    return base64.b64encode(b).decode('ascii')


def b64decode(txt):
    if type(txt) is not str:
        raise ValueError('non-base64 data')
    try:
        return base64.b64decode(txt, validate=True)
    except (ValueError, Exception) as e:
        raise ValueError('malformed base64') from e


def pub_bytes(pub):
    return pub.public_bytes(encoding=serialization.Encoding.Raw,
                            format=serialization.PublicFormat.Raw)


def read_regular(path, limit):
    """Read one stable non-symlink FD; shared advisory lock with journal writers."""
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise ValueError('non-regular or over-limit file')
        fcntl.flock(fd, fcntl.LOCK_SH)
        with os.fdopen(fd, 'rb', closefd=False) as f:
            data = f.read(limit + 1)
        if len(data) > limit:
            raise ValueError('file exceeds permitted bytes')
        return data
    finally:
        os.close(fd)


def private_key(path):
    if Path(path).is_symlink():
        raise ValueError('private key symlink is not permitted')
    perms = Path(path).stat().st_mode & 0o777
    if perms & 0o077:
        raise ValueError('private key must be owner-only (chmod 600)')
    data = read_regular(path, 512)
    key = serialization.load_pem_private_key(data, password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError('Ed25519 key required')
    return key


def public_key(path):
    data = read_regular(path, 512)
    key = serialization.load_pem_public_key(data)
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError('trusted public key must be Ed25519')
    return key


def create_no_overwrite(path, data):
    """Owner-only, exclusive creation, no symlink follow; durable file & dir."""
    path = Path(path)
    if not path.parent.is_dir() or path.parent.is_symlink():
        raise ValueError('output parent must be existing regular directory')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    try:
        with os.fdopen(fd, 'wb', closefd=False) as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
    finally:
        os.close(fd)
    folder = os.open(path.parent, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
    try:
        os.fsync(folder)
    finally:
        os.close(folder)


def keygen(private, public):
    private, public = Path(private), Path(public)
    if private.resolve() == public.resolve():
        raise ValueError('private and public outputs must differ')
    if private.exists() or public.exists():
        raise ValueError('key output already exists')
    key = Ed25519PrivateKey.generate()
    secret = key.private_bytes(serialization.Encoding.PEM,
                               serialization.PrivateFormat.PKCS8,
                               serialization.NoEncryption())
    pub = key.public_key().public_bytes(serialization.Encoding.PEM,
                                        serialization.PublicFormat.SubjectPublicKeyInfo)
    create_no_overwrite(private, secret)
    create_no_overwrite(public, pub)
    return {'public_key_sha256': sha(pub_bytes(key.public_key())),
            'private_key_file': str(private), 'public_key_file': str(public),
            'warning': 'Keep private key OUTSIDE repositories, backups and shared folders'}


def validate_journal(kind, raw):
    if kind == 'worker':
        if len(raw) > MAX_LEDGER_BYTES['worker']:
            raise ValueError('worker journal limit exceeded')
        if raw and not raw.endswith(b'\n'):
            raise ValueError('worker journal missing terminating newline')
        rows = worker.load(raw)
        result = worker.verify_rows(rows)
        expected = b''.join(worker.canon(row)+b'\n' for row in rows)
        if raw != expected:
            raise ValueError('worker journal is not canonical')
        return {'count':result['stages'], 'head':result['head'],
                'proof_scope':result['proof_scope'], 'globally_complete':False}
    if kind == 'source':
        rows = source.parse_journal(raw)
        result = source.verify(rows)
        expected = b''.join(source.canonical(row)+b'\n' for row in rows)
        if raw != expected:
            raise ValueError('source journal is not canonical')
        return {'count':result['events'], 'head':result['tip_sha256'],
                'proof_scope':'STRUCTURAL_CHAIN_ONLY', 'globally_complete':False}
    raise ValueError('unknown journal')


def signed(body, key):
    return {'body':body, 'signature_ed25519_b64':b64(key.sign(canonical(body)))}


def check_signature(signed_obj, key, expected_keys):
    if type(signed_obj) is not dict or set(signed_obj)!={'body','signature_ed25519_b64'}:
        raise ValueError('signed wrapper schema defect')
    body = signed_obj['body']
    if type(body) is not dict or set(body)!=expected_keys:
        raise ValueError('signed body schema defect')
    signature = b64decode(signed_obj['signature_ed25519_b64'])
    if len(signature)!=64:
        raise ValueError('invalid signature length')
    try:
        key.verify(signature, canonical(body))
    except InvalidSignature as e:
        raise ValueError('signature is invalid') from e
    return body


def snapshot(worker_path, source_path, private_path, snapshot_path, anchor_path):
    out1, out2=Path(snapshot_path),Path(anchor_path)
    if out1.resolve()==out2.resolve() or out1.exists() or out2.exists():
        raise ValueError('snapshot and anchor must be distinct new files')
    sources = {'worker':Path(worker_path), 'source':Path(source_path)}
    for path in sources.values():
        if path.resolve() in (out1.resolve(), out2.resolve()):
            raise ValueError('journal overlaps output destination')
    # For a synchronized multi-journal snapshot a cross-file transaction is
    # required; here each independently held lock gives a valid per-file cut.
    files = {}
    metadata = {}
    for kind,path in sources.items():
        raw=read_regular(path,MAX_LEDGER_BYTES[kind])
        metadata[kind]=validate_journal(kind,raw)
        files[kind]={'sha256':sha(raw),'length':len(raw),'base64':b64(raw)}
    signer=private_key(private_path)
    fingerprint=sha(pub_bytes(signer.public_key()))
    timestamp=datetime.now(timezone.utc).isoformat(timespec='seconds')
    body={'protocol':FORMAT,'created_utc':timestamp,
          'public_key_sha256':fingerprint,'journals':files,'proof_claims':metadata,
          'provenance':'LOCAL_FILE_READ_NOT_EXTERNAL_SOURCE_ATTESTATION',
          'service_deployment_authorized':False,'trading_authorized':False}
    archive=signed(body,signer)
    archive_bytes=canonical(archive)+b'\n'
    abody={'protocol':ANCHOR_FORMAT,'archive_sha256':sha(archive_bytes),
           'created_utc':timestamp,'public_key_sha256':fingerprint,
           'worker_head':metadata['worker']['head'],
           'source_head':metadata['source']['head']}
    anchor=signed(abody,signer)
    # Never overwrite existing anchor/snapshot, avoid silent replacement.
    create_no_overwrite(out1,archive_bytes)
    create_no_overwrite(out2,canonical(anchor)+b'\n')
    return {'status':'SIGNED_LOCAL_SNAPSHOT_CREATED',
            'snapshot':str(out1),'anchor':str(out2),
            'snapshot_sha256':abody['archive_sha256'],
            'public_key_sha256':fingerprint,
            'external_anchor_published':False,
            'worker_stages':metadata['worker']['count'],
            'source_events':metadata['source']['count']}


def verify(snapshot_path, anchor_path, public_path):
    key=public_key(public_path)
    trusted=sha(pub_bytes(key))
    snapraw=read_regular(snapshot_path,MAX_SNAPSHOT_BYTES)
    anchorraw=read_regular(anchor_path,4096)
    archive=json.loads(snapraw)
    anchor=json.loads(anchorraw)
    body=check_signature(archive,key,{'protocol','created_utc','public_key_sha256','journals',
                                      'proof_claims','provenance','service_deployment_authorized','trading_authorized'})
    abody=check_signature(anchor,key,{'protocol','archive_sha256','created_utc',
                                      'public_key_sha256','worker_head','source_head'})
    if (body['protocol']!=FORMAT or abody['protocol']!=ANCHOR_FORMAT or
        body['public_key_sha256']!=trusted or abody['public_key_sha256']!=trusted or
        body['created_utc']!=abody['created_utc'] or
        body['provenance']!='LOCAL_FILE_READ_NOT_EXTERNAL_SOURCE_ATTESTATION' or
        body['service_deployment_authorized'] is not False or body['trading_authorized'] is not False):
        raise ValueError('inconsistent anchor/security claims')
    if snapraw!=canonical(archive)+b'\n' or anchorraw!=canonical(anchor)+b'\n':
        raise ValueError('noncanonical signed file')
    if sha(snapraw)!=abody['archive_sha256']:
        raise ValueError('detached anchor archive mismatch')
    if type(body['journals']) is not dict or set(body['journals']) != {'worker','source'}:
        raise ValueError('journal table schema defect')
    if type(body['proof_claims']) is not dict or set(body['proof_claims']) != {'worker','source'}:
        raise ValueError('claim table schema defect')
    decoded={}
    for name in ('worker','source'):
        ent=body['journals'][name]
        if type(ent) is not dict or set(ent) != {'sha256','length','base64'}:
            raise ValueError('blob schema defect')
        data=b64decode(ent['base64'])
        if (len(data)>MAX_LEDGER_BYTES[name] or type(ent['length']) is not int or
            len(data)!=ent['length'] or sha(data)!=ent['sha256'] or
            validate_journal(name,data)!=body['proof_claims'][name]):
            raise ValueError('journal mismatch or invalid certificate')
        decoded[name]=data
    if (body['proof_claims']['worker']['head']!=abody['worker_head'] or
        body['proof_claims']['source']['head']!=abody['source_head']):
        raise ValueError('anchor does not match journal heads')
    return {'status':'SIGNED_SNAPSHOT_AND_FINITE_PROOFS_VERIFIED',
            'public_key_sha256':trusted,'snapshot_sha256':sha(snapraw),
            'worker_stages':body['proof_claims']['worker']['count'],
            'source_events':body['proof_claims']['source']['count'],
            'externally_published_anchor_checked':False,
            'globally_complete':False,'live_trading_authorized':False},decoded


def restore(snapshot_path, anchor_path, public_path, output_directory):
    result, decoded=verify(snapshot_path,anchor_path,public_path)
    dest=Path(output_directory)
    if dest.exists() or dest.is_symlink():
        raise ValueError('restore destination must NOT exist: non-destructive recovery only')
    if not dest.parent.is_dir() or dest.parent.is_symlink():
        raise ValueError('restore parent must exist and not be a symlink')
    dest.mkdir(mode=0o700)
    try:
        create_no_overwrite(dest/'cosmic-love.jsonl',decoded['worker'])
        create_no_overwrite(dest/'source-receipts.jsonl',decoded['source'])
        report={'protocol':FORMAT,'status':'RESTORED_IN_ISOLATED_DIRECTORY',
                'snapshot_sha256':result['snapshot_sha256'],
                'public_key_sha256':result['public_key_sha256'],
                'worker_stages':result['worker_stages'],
                'source_events':result['source_events'],
                'automatic_production_restore':False,'live_trading_authorized':False}
        create_no_overwrite(dest/'RESTORE_REPORT.json',canonical(report)+b'\n')
        return report
    except Exception:
        # Do not delete unverified work or recursively erase user directories.
        raise


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    gen=sub.add_parser('keygen');gen.add_argument('--private',required=True);gen.add_argument('--public',required=True)
    back=sub.add_parser('snapshot')
    for flag in ('worker','source','private','snapshot','anchor'):
        back.add_argument('--'+flag,required=True)
    for name in ('verify','restore'):
        p=sub.add_parser(name)
        for flag in ('snapshot','anchor','trusted-public'):
            p.add_argument('--'+flag,required=True)
        if name=='restore':p.add_argument('--dest-dir',required=True)
    args=parser.parse_args(argv)
    try:
        if args.command=='keygen':
            r=keygen(args.private,args.public)
        elif args.command=='snapshot':
            r=snapshot(args.worker,args.source,args.private,args.snapshot,args.anchor)
        elif args.command=='verify':
            r,_=verify(args.snapshot,args.anchor,args.trusted_public)
        else:
            r=restore(args.snapshot,args.anchor,args.trusted_public,args.dest_dir)
        print(json.dumps(r,indent=2,sort_keys=True,ensure_ascii=False))
        return 0
    except (ValueError,OSError,TypeError,json.JSONDecodeError,InvalidSignature) as e:
        print('HOLD: '+type(e).__name__+': '+str(e),file=sys.stderr)
        return 2

if __name__=='__main__':sys.exit(main())
