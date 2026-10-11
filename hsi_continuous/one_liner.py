#!/usr/bin/env python3
"""Translate an audited HSI entrypoint to a <=2048-byte POSIX one-line launcher.

The launcher is a reference to a locally installed reviewed implementation,
not a lossless compression of arbitrary source code. Never execute it during
translation. Reject any target outside the allowlist.
"""
import argparse
import json
from pathlib import Path
import shlex

ROOT=Path(__file__).resolve().parent.parent
NOTES=ROOT/"Notes"
ALLOW={
 "originalxy": "Notes/HSI_Prime_Analytic_2KB_Release/HSI_OriginalXY_Plaintext_Core.py",
 "feedback": "hsi_continuous/riemann_feedback.py",
 "review": "hsi_continuous/review.py",
}
PROTOCOL="HSI-2KB-TRANSLATOR/0.1"

def build(name):
    if name not in ALLOW:
        raise ValueError("entrypoint not allowlisted")
    relative=ALLOW[name]
    source=ROOT/relative
    if not source.is_file():
        raise FileNotFoundError(relative)
    payload=source.read_bytes()
    encoded=1
    for byte in payload:
        encoded=encoded*257+byte+1
    recovered=[]
    n=encoded
    while n>1:
        n,r=divmod(n,257)
        if not r: raise ValueError('invalid E257 digit')
        recovered.append(r-1)
    if bytes(reversed(recovered))!=payload:
        raise AssertionError('E257 roundtrip failed')
    # The launcher is small; E257 is stored in a separate reversible manifest.
    # No cryptographic integrity/authentication claim is made.
    line=("set -eu; p="+shlex.quote(relative)+"; "
          "test -f \"$p\" || { echo 'HSI source missing' >&2; exit 2; }; "
          "command -v python3 >/dev/null 2>&1 || exit 127; "
          "exec python3 \"$p\" \"$@\"")
    data=(line+"\n").encode("utf-8")
    if b"\n" in data[:-1] or len(data)>2048:
        raise AssertionError("not a <=2KB single physical line")
    return {"protocol":PROTOCOL,"entrypoint":name,"target":relative,
            "source_e257":str(encoded),"one_liner_bytes":len(data),
            "self_contained":False,"launcher":line}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--entrypoint",choices=sorted(ALLOW),default="feedback")
    p.add_argument("--out",default="hsi_continuous/out")
    a=p.parse_args()
    r=build(a.entrypoint)
    out=(ROOT/a.out).resolve()
    if not out.is_relative_to(ROOT) or out.is_relative_to(NOTES.resolve()):
        raise ValueError("output outside allowed area")
    out.mkdir(parents=True,exist_ok=True)
    (out/(a.entrypoint+".oneline.sh")).write_text(r["launcher"]+"\n",encoding="utf-8")
    (out/(a.entrypoint+".oneline.json")).write_text(json.dumps(
        {k:v for k,v in r.items() if k!="launcher"},indent=2)+"\n",encoding="utf-8")
    print(f"{PROTOCOL}: {a.entrypoint}, {r['one_liner_bytes']} bytes, referenced source only")

if __name__=="__main__":
    main()
