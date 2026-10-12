#!/usr/bin/env python3
"""Review-only HSI-ST/1 worker: perpetual heartbeat, finite proof, durable journal.

No ChatGPT/GitHub/Railway/Render/Dropbox API calls, code edits, or trading.
A local SHA-256 chain is NOT externally anchored and is NOT a proof of truth.
"""
import argparse
import fcntl
import hashlib
import json
import os
import time
from math import isqrt
from pathlib import Path

TAG = 'COSMIC-LOVE-CLOSURE-WORKER/1.0'
ZERO = '0'*64
AUTH = {'trade':False,'deploy':False,'merge':False,'network':False}

def canon(v):
    return json.dumps(v, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()

def sha(v):
    return hashlib.sha256(v).hexdigest()

def program(k):
    assert type(k) is int and 2 <= k <= 64 and k%2 == 0
    K=k+1; B=4*K
    c=sum((((2*a+1-q%2)*K+(q^1))*B**(2*q+a)) for q in range(k) for a in (0,1))
    v=c+k-1
    return v*(v+1)//2+c

def decode(p):
    v=(isqrt(8*p+1)-1)//2
    c=p-v*(v+1)//2
    return v-c+1,c

def transition(k,c,q,a):
    K=k+1; B=4*K
    u=c//B**(2*q+a)%B
    z,r=divmod(u,K)
    return (r,z//2,2*(z%2)-1)

def prove(k,p,old):
    if type(p) is not int or k < 2 or k > 64 or k%2 or p!=program(k):
        raise ValueError('noncanonical stage')
    nk,c=decode(p)
    if nk!=k:raise ValueError('invalid HSI-ST/1 decoder')
    new=[]
    for q in range(k):
        for a in (0,1):
            r,b,d=transition(k,c,q,a)
            if (r,b,d)!=(q^1,a,1-2*(q%2)):
                raise ValueError('transition defect')
            if transition(k,c,r,b)!=(q,a,-d):
                raise ValueError('cycle defect')
            new.append((q,a,r,b,d))
    if new[:len(old)]!=old:
        raise ValueError('not a conservative extension')
    return new

def verify_rows(rows):
    if type(rows) is not list or len(rows)>32:
        raise ValueError('invalid event count')
    last=ZERO;old=[]
    for i,row in enumerate(rows):
        if type(row) is not dict or set(row)!={'protocol','stage','k','p','prev','rules_sha256','scope','authorization','digest'}:
            raise ValueError('unexpected event keys')
        k=2*(i+1)
        if row['protocol']!=TAG or type(row['stage']) is not int or row['stage']!=i or type(row['k']) is not int or row['k']!=k or row['prev']!=last:
            raise ValueError('invalid stage chain')
        if type(row['p']) is not str or not row['p'].isdigit() or len(row['p'])>1024:
            raise ValueError('invalid program integer')
        p=int(row['p']);new=prove(k,p,old)
        if row['rules_sha256']!=sha(canon(new)):
            raise ValueError('invalid rule certificate')
        if row['scope']!='ALL_FINITE_TAPES_ACTIVE_CONFIGURATIONS' or row['authorization']!=AUTH:
            raise ValueError('unlicensed assertion')
        if row['digest']!=sha(canon({key:val for key,val in row.items() if key!='digest'})):
            raise ValueError('broken event digest')
        old,last=new,row['digest']
    return {'protocol':TAG,'status':'FINITE_CHAIN_VERIFIED','stages':len(rows),'head':last,
            'proof_scope':'ALL_FINITE_TAPES_ACTIVE_CONFIGURATIONS',
            'globally_complete':False,'externally_anchored':False,
            'live_trading_authorized':False}

def load(data):
    if len(data)>1024*1024:raise ValueError('journal too big')
    lines=data.splitlines()
    if len(lines)>32:raise ValueError('journal too long')
    rows=[json.loads(x) for x in lines if x.strip()]
    verify_rows(rows)
    return rows

def advance(path, ceiling):
    path=Path(path)
    if path.is_symlink():raise ValueError('symlink journal')
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+b') as f:
        fcntl.flock(f.fileno(),fcntl.LOCK_EX)
        try:
            f.seek(0);rows=load(f.read())
            k=2*(len(rows)+1)
            if k>ceiling:return None
            p=program(k)
            new=prove(k,p,[] if not rows else prove(k-2,int(rows[-1]['p']),[]))
            event={'protocol':TAG,'stage':len(rows),'k':k,'p':str(p),
                   'prev':rows[-1]['digest'] if rows else ZERO,
                   'rules_sha256':sha(canon(new)),
                   'scope':'ALL_FINITE_TAPES_ACTIVE_CONFIGURATIONS','authorization':AUTH.copy()}
            event['digest']=sha(canon(event))
            verify_rows(rows+[event])
            f.seek(0,os.SEEK_END)
            f.write(canon(event)+b'\n');f.flush();os.fsync(f.fileno())
            return event
        finally:
            fcntl.flock(f.fileno(),fcntl.LOCK_UN)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--ledger',default='/data/cosmic-love.jsonl')
    p.add_argument('--max-states',type=int,default=32)
    p.add_argument('--interval',type=float,default=60)
    p.add_argument('--check',action='store_true')
    a=p.parse_args()
    if not (2<=a.max_states<=64 and a.max_states%2==0 and .1<=a.interval<=86400):
        p.error('unsafe parameters')
    path=Path(a.ledger)
    if a.check:
        if path.is_symlink():raise SystemExit('symlink forbidden')
        rows=load(path.read_bytes()) if path.exists() else []
        print(json.dumps(verify_rows(rows),sort_keys=True));return
    while True:
        result=advance(path,a.max_states)
        if result is not None:print('COSMIC_LOVE',flush=True)
        else:print('HOLD_RESOURCE_LIMIT',flush=True)
        time.sleep(a.interval)

if __name__=='__main__':main()
