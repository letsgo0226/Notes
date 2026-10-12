"""HSI-ST/1 <-> Original-XY <-> UVCM finite semantic comparison.

The original algorithms are reimplemented as independent bounded transition
functions. This is NOT a byte-for-byte comparison of their checkpoint formats.
"""
from __future__ import annotations

from math import isqrt
from pleiadian_blue.uvcm import advance, initial


def unpair(n):
    assert type(n) is int and n >= 0
    w=(isqrt(8*n+1)-1)//2
    return n-w*(w+1)//2, w-(n-w*(w+1)//2)+1


def decode_st(p):
    """Original HSI-ST/1 transition encoding: 8-bit cells, 2-symbol TM."""
    c,k=unpair(p)
    K=k+1
    B=4*K
    table={}
    for q in range(k):
        for bit in (0,1):
            u=c//(B**(2*q+bit))%B
            newq=u%K
            v=u//K
            move=2*(v%2)-1
            write=v//2
            table[f"q{q}:{bit}"]=[write,move,"HALT" if newq==k else f"q{newq}"]
    return {"start":"q0","halt":"HALT","transitions":table},k


def original_xy_step(p,q,h,ones):
    """Independent reference from the HSI-ORIGINAL-XY/2K finite transition."""
    c,k=unpair(p)
    K=k+1
    B=4*K
    if q==k:
        return q,h,set(ones)
    bit=int(h in ones)
    u=c//(B**(2*q+bit))%B
    nq=u%K
    v=u//K
    move=2*(v%2)-1
    write=v//2
    new_ones=set(ones)
    if write:new_ones.add(h)
    else:new_ones.discard(h)
    return nq,h+move,new_ones


def st_byte_step(p,q,h,byte_cells):
    """Independent reference of ST's 8-bit-per-cell disk-tape semantics."""
    c,k=unpair(p)
    K=k+1
    B=4*K
    if q==k:
        return q,h,dict(byte_cells)
    cell,offset=divmod(h,8)
    v=byte_cells.get(cell,0)
    bit=(v>>offset)&1
    u=c//(B**(2*q+bit))%B
    nq=u%K
    w=u//K
    v=(v | (1<<offset)) if w//2 else (v & ~(1<<offset))
    out=dict(byte_cells)
    if v:out[cell]=v
    else:out.pop(cell,None)
    return nq,h+2*(w%2)-1,out


def bitset_to_bytes(ones):
    result={}
    for h in ones:
        cell,offset=divmod(h,8)
        result[cell]=result.get(cell,0)|(1<<offset)
    return result


def bytes_to_bitset(cells):
    return {8*cell+bit for cell,value in cells.items()
            for bit in range(8) if value>>bit&1}


def compare(p,bits,steps):
    """Finite bounded independent triple comparison on one common tape."""
    assert type(p) is int and 0<=p<=100000
    assert type(steps) is int and 0<=steps<=256
    assert len(bits)<=128 and all(b in "01" for b in bits)
    spec,k=decode_st(p)
    uv=initial(spec,bits)
    oq,oh,ones=0,0,{i for i,b in enumerate(bits) if b=="1"}
    sq,sh,bytecells=0,0,bitset_to_bytes(ones)
    for t in range(steps+1):
        st_ones=bytes_to_bitset(bytecells)
        expected_q="HALT" if oq==k else f"q{oq}"
        st_q="HALT" if sq==k else f"q{sq}"
        assert uv["q"]==expected_q==st_q, (p,bits,t,"q")
        assert uv["h"]==oh==sh, (p,bits,t,"h")
        assert set(uv["ones"])==ones==st_ones, (p,bits,t,"tape")
        if t==steps or oq==k:
            break
        uv,_=advance(spec,uv,1)
        oq,oh,ones=original_xy_step(p,oq,oh,ones)
        sq,sh,bytecells=st_byte_step(p,sq,sh,bytecells)
    return {"p":p,"bits":bits,"steps_verified":t,
            "status":"HALTED" if oq==k else "UNRESOLVED_BUDGET",
            "final_q":uv["q"],"head":uv["h"],"ones":uv["ones"],
            "triple_equivalent":True}


def sweep():
    # Finite exhaustive sample; NOT a universal proof for arbitrary p/inputs.
    checks=0
    for p in range(128):
        for bits in ("","0","1","101","00110"):
            compare(p,bits,12)
            checks+=1
    for p in (1829,1024,2048,4095,9999):
        for bits in ("","1","010101","11110000"):
            compare(p,bits,40)
            checks+=1
    return {"protocol":"HSI-UVCM-CROSSKERNEL/1","cases":checks,
            "result":"FINITE_CASES_PASSED",
            "not_claimed":["unbounded_halting","hardware_limit_removal",
                           "all_p_universality","checkpoint_format_identity"]}


if __name__=="__main__":
    import json
    print(json.dumps(sweep(),sort_keys=True))
