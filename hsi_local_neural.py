#!/usr/bin/env python3
import argparse, hashlib, json, os, sys, time, urllib.request, urllib.error, urllib.parse
from pathlib import Path

PROTOCOL="HSI-LOCAL-NEURAL/1.0"
VERSION="1.0.0"
BLUE=b"PLEIADIAN-BLUE"
BASE=os.getenv("HSI_NEURAL_BASE","http://127.0.0.1:8001").rstrip("/")
TIMEOUT=int(os.getenv("HSI_NEURAL_TIMEOUT","1800"))
POLL=float(os.getenv("HSI_NEURAL_POLL","2"))
E257_ENABLED=os.getenv("HSI_E257","1")!="0"

if hasattr(sys,"set_int_max_str_digits"): sys.set_int_max_str_digits(0)

def e257(data):
    n=1
    for b in data:n=n*257+b+1
    return n

def d257(n):
    out=bytearray()
    while n>1:
        n,r=divmod(n,257)
        if not 1<=r<=256: raise ValueError("invalid E257")
        out.append(r-1)
    out.reverse()
    return bytes(out)

def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":"))

def req(path,payload=None,timeout=120):
    url=BASE+path
    data=None;headers={}
    if payload is not None:
        data=canon(payload).encode("utf-8");headers["Content-Type"]="application/json"
    r=urllib.request.Request(url,data=data,headers=headers)
    try:
        with urllib.request.urlopen(r,timeout=timeout) as x:
            raw=x.read()
    except urllib.error.HTTPError as e:
        body=e.read().decode("utf-8","replace")
        raise RuntimeError("HTTP %s %s: %s"%(e.code,path,body)) from None
    except urllib.error.URLError as e:
        raise RuntimeError("cannot reach local neural renderer at %s: %s"%(BASE,e.reason)) from None
    try:return json.loads(raw.decode("utf-8"))
    except Exception: raise RuntimeError("invalid JSON from %s: %r"%(path,raw[:300])) from None

def download(rel):
    url=rel if rel.startswith(("http://","https://")) else BASE+("/" if not rel.startswith("/") else "")+rel
    with urllib.request.urlopen(url,timeout=600) as r:return r.read()

def write_e257(path,raw,chunk=128):
    ok=True;count=0
    with open(path,"w",encoding="utf-8") as f:
        f.write("[")
        first=True
        for i in range(0,len(raw),chunk):
            b=raw[i:i+chunk];n=e257(b);ok=ok and d257(n)==b
            if not first:f.write(",")
            f.write(str(n));first=False;count+=1
        f.write("]\n")
    return count,ok

def main():
    p=argparse.ArgumentParser(description="HSI Local Neural Renderer")
    p.add_argument("keywords",nargs="*")
    p.add_argument("--out",default=os.getenv("HSI_OUT"))
    a=p.parse_args()
    q=" ".join(a.keywords).strip()
    if not q:q=input("keywords> ").strip()
    if not q:raise SystemExit("keywords required")

    health=req("/health",timeout=30)
    if health.get("code")!=200:raise SystemExit("local renderer unhealthy: "+canon(health))

    qb=q.encode("utf-8");basis=e257(qb);seed=basis%2147483647 or 1
    payload={
        "sample_query":q,
        "thinking":True,
        "use_random_seed":False,
        "seed":seed,
        "batch_size":1,
        "audio_format":"wav"
    }
    out=Path(a.out).expanduser() if a.out else Path.home()/"Music"/"HSI-Neural"/(time.strftime("%Y%m%d-%H%M%S")+"-"+str(os.getpid()))
    out.mkdir(parents=True,exist_ok=True)
    (out/"keywords.txt").write_text(q+"\n",encoding="utf-8")
    (out/"request.json").write_text(canon({"protocol":PROTOCOL,"payload":payload})+"\n",encoding="utf-8")

    print("protocol>",PROTOCOL)
    print("output>",out)
    print("backend>",BASE)
    print("seed>",seed)
    print("submit> runtime input only; no HSI creative presets")

    created=req("/release_task",payload,timeout=120)
    if created.get("code")!=200:raise SystemExit("submit failed: "+canon(created))
    task=(created.get("data") or {}).get("task_id")
    if not task:raise SystemExit("missing task_id: "+canon(created))
    print("task>",task)

    started=time.time();final=None
    while time.time()-started<TIMEOUT:
        status=req("/query_result",{"task_id_list":[task]},timeout=120)
        rows=status.get("data") or []
        if not rows:
            time.sleep(POLL);continue
        row=rows[0];st=int(row.get("status",0))
        if st==0:
            elapsed=int(time.time()-started)
            print("running>",elapsed,"s",flush=True)
            time.sleep(POLL);continue
        if st==2:raise SystemExit("generation failed: "+canon(row))
        if st==1:
            final=row;break
        time.sleep(POLL)
    if final is None:raise SystemExit("generation timeout")

    result=final.get("result")
    if isinstance(result,str):
        result=json.loads(result)
    if not isinstance(result,list) or not result:raise SystemExit("empty generation result")
    item=result[0]
    if int(item.get("status",1))!=1:raise SystemExit("generation result not successful: "+canon(item))
    rel=item.get("file")
    if not rel:raise SystemExit("missing audio file URL")

    raw=download(rel)
    wav=out/"song.wav";wav.write_bytes(raw)
    lyrics=item.get("lyrics") or ""
    prompt=item.get("prompt") or ""
    metas=item.get("metas") or {}
    if lyrics:(out/"lyrics.txt").write_text(lyrics+"\n",encoding="utf-8")
    (out/"result.json").write_text(canon(item)+"\n",encoding="utf-8")

    chunks=0;eok=True
    if E257_ENABLED:
        chunks,eok=write_e257(out/"song.e257",raw)

    checks={
        "audio_nonempty":len(raw)>1024,
        "keywords_roundtrip":d257(basis)==qb,
        "blue_roundtrip":d257(e257(BLUE))==BLUE,
        "e257_audio_roundtrip":eok
    }
    cert={
        "protocol":PROTOCOL,"version":VERSION,
        "generation_input":"runtime-keywords-only",
        "creative_presets":[],
        "generation_basis_e257":basis,
        "deterministic_seed":seed,
        "blue_e257":e257(BLUE),
        "blue_role":"certificate-normative-only",
        "blue_conditioning":False,
        "renderer":"ACE-Step-1.5-local",
        "neural_renderer":True,
        "local_model":True,
        "local_http_api":True,
        "external_cloud":False,
        "external_paid_api":False,
        "task_id":task,
        "dit_model":item.get("dit_model"),
        "lm_model":item.get("lm_model"),
        "model_prompt":prompt,
        "model_lyrics":lyrics,
        "model_metas":metas,
        "seed_value":item.get("seed_value"),
        "audio_bytes":len(raw),
        "audio_sha256":hashlib.sha256(raw).hexdigest(),
        "e257_enabled":E257_ENABLED,
        "e257_chunk_bytes":128 if E257_ENABLED else 0,
        "e257_chunks":chunks,
        "checks":checks
    }
    cert["closed"]=int(all(checks.values()))
    (out/"song.hsicert").write_text(canon(cert)+"\n",encoding="utf-8")
    files=["keywords.txt","request.json","result.json","song.wav","song.hsicert"]
    if lyrics:files.append("lyrics.txt")
    if E257_ENABLED:files.append("song.e257")
    (out/"manifest.json").write_text(canon({"protocol":PROTOCOL,"output":str(out),"files":files,"closed":cert["closed"]})+"\n",encoding="utf-8")
    print("audio>",wav)
    print("bytes>",len(raw))
    print("sha256>",cert["audio_sha256"])
    print("closed>",cert["closed"])
    raise SystemExit(0 if cert["closed"] else 3)

if __name__=="__main__":main()
