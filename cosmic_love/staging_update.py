#!/usr/bin/env python3
"""Proof-gated, bounded staging-update PROPOSALS only.

This program cannot write GitHub, call Railway, access conversations or trade.
Code deployment requires a distinct CI-and-host control plane. See spec.
"""
import argparse
import hashlib
import json
import re
import sys
from math import isqrt

PROTOCOL='COSMIC-LOVE-STAGING-PROPOSAL/1'
ZERO='0'*64
MAX_K=32
CAPABILITIES={'scope':'ISOLATED_STAGING_ONLY',
              'deploy':'REQUIRES_SEPARATE_INDEPENDENT_CI_AND_HOST_CONTROL',
              'merge_main':False,'trading':False,'personal_data':False,
              'runtime_can_deploy_itself':False}
SHA=re.compile(r'[0-9a-f]{40}\Z')
DIGEST=re.compile(r'[0-9a-f]{64}\Z')

def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()

def hashobj(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()

def tm_program(k):
    if type(k) is not int or k<2 or k>MAX_K or k%2:
        raise ValueError('invalid bounded state count')
    K=k+1;B=4*K
    c=sum(((2*a+1-(q%2))*K+(q^1))*B**(2*q+a) for q in range(k) for a in (0,1))
    v=c+k-1
    return v*(v+1)//2+c

def decode_tm(p):
    v=(isqrt(8*p+1)-1)//2
    c=p-v*(v+1)//2
    k=v-c+1;K=k+1;B=4*K
    return k,[(q,a,(u:=c//B**(2*q+a)%B)%K,
               u//K//2,2*((u//K)%2)-1) for q in range(k) for a in (0,1)]

def rules(k):
    p=tm_program(k)
    d,rows=decode_tm(p)
    if d!=k or len(rows)!=2*k:
        raise ValueError('HSI-ST/1 decode mismatch')
    for q,a,r,b,move in rows:
        if (r,b,move)!=(q^1,a,1-2*(q%2)):
            raise ValueError('nonconforming transition')
        partner=rows[2*r+b]
        if partner[2:]!=(q,a,-move):
            raise ValueError('two-step closed loop invalid')
    return p,rows

def body(stage,previous_sha,commit):
    k=2*(stage+1);p,rows=rules(k)
    old=rules(k-2)[1] if k>2 else []
    if rows[:len(old)]!=old:
        raise ValueError('old rules were modified')
    return {'protocol':PROTOCOL,'sequence':stage,'k':k,'p':str(p),
            'previous_sha256':previous_sha,'rules_sha256':hashobj(rows),
            'verified_scope':'ALL_FINITE_TAPES_FOR_THIS_ACTIVE_TM',
            'source_commit':commit,'capabilities':CAPABILITIES.copy(),
            'status':'CANDIDATE_REVIEW_ONLY'}

def verify(events):
    if type(events) is not list or len(events)>MAX_K//2:
        raise ValueError('invalid candidate list')
    prev=ZERO;last_rules=[]
    for i,ev in enumerate(events):
        if type(ev) is not dict or set(ev)!={'body','digest'}:
            raise ValueError('record fields invalid')
        b=ev['body']
        if type(b) is not dict or set(b)!=set(body(i,prev,'0'*40)):
            raise ValueError('body fields invalid')
        commit=b.get('source_commit')
        if type(commit) is not str or not SHA.fullmatch(commit):
            raise ValueError('invalid pinned commit')
        expected=body(i,prev,commit)
        if b!=expected or type(ev['digest']) is not str or not DIGEST.fullmatch(ev['digest']) or ev['digest']!=hashobj(b):
            raise ValueError('modified or unverified candidate')
        _,new=rules(b['k'])
        if new[:len(last_rules)]!=last_rules:
            raise ValueError('nonconservative evolution')
        prev=ev['digest'];last_rules=new
    return {'protocol':PROTOCOL,'status':'FINITE_STAGING_CANDIDATES_VERIFIED',
            'events':len(events),'head':prev,'automatic_production_deploy':False,
            'runtime_self_deploy':False,'real_order_permission':False}

def next_candidate(events,commit):
    verify(events)
    if type(commit) is not str or not SHA.fullmatch(commit):
        raise ValueError('exact 40-hex source commit required')
    if len(events)>=MAX_K//2:
        raise ValueError('bounded state ceiling reached; HOLD')
    prev=events[-1]['digest'] if events else ZERO
    b=body(len(events),prev,commit)
    return {'body':b,'digest':hashobj(b)}

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--mode',choices=('propose','check'),required=True)
    parser.add_argument('--chain',required=True)
    parser.add_argument('--source-commit')
    options=parser.parse_args(argv)
    try:
        with open(options.chain,'rb') as f:
            data=f.read(1024*1024+1)
        if len(data)>1024*1024:raise ValueError('chain too long')
        events=json.loads(data)
        verified=verify(events)
        if options.mode=='check':result=verified
        else:result=next_candidate(events,options.source_commit)
        print(json.dumps(result,sort_keys=True,ensure_ascii=False,indent=2))
        return 0
    except (ValueError,OSError,TypeError,KeyError,json.JSONDecodeError) as e:
        print('HOLD: '+str(e),file=sys.stderr)
        return 2

if __name__=='__main__':sys.exit(main())
