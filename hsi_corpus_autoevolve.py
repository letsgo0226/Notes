#!/usr/bin/env python3
"""HSI Corpus bounded endogenous DSP-policy update solver.

Enumerates permitted render-policy proposals, generates ACTUAL WAV files with
existing locked corpus sources, independently verifies each candidate, and
writes a deployment proposal only when a candidate improves a predeclared
measurable structure criterion. No code rewrite or GitHub write is performed.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PROTOCOL="HSI-CORPUS-AUTOEVOLVE/1.0"
POLICY_PROTOCOL="HSI-CORPUS-RENDER-POLICY/1.0"
PROPOSALS=[
  {"event_boost":1,"fade_ms":180,"gain_scale":1.0},
  {"event_boost":2,"fade_ms":180,"gain_scale":1.0},
  {"event_boost":1,"fade_ms":220,"gain_scale":.9},
  {"event_boost":2,"fade_ms":150,"gain_scale":1.1},
  {"event_boost":3,"fade_ms":240,"gain_scale":.9},
  {"event_boost":4,"fade_ms":180,"gain_scale":1.0},
]

def canon(x):
    return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":"))

def jsonfile(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def require(ok,msg):
    if not ok:raise ValueError(msg)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--baseline",required=True,help="Previously verified HSI output directory")
    p.add_argument("--lock",required=True,help="Corpus lock with cached source audio")
    p.add_argument("--out",required=True,help="Isolated output directory for proposals")
    p.add_argument("--start",type=int,default=0,help="Resume candidate index")
    p.add_argument("--max-candidates",type=int,default=6)
    p.add_argument("keywords",nargs="+")
    a=p.parse_args()
    root=Path(a.out).expanduser().resolve();root.mkdir(parents=True,exist_ok=True)
    baseline=Path(a.baseline).resolve()
    require(baseline!=root,"proposal output must be isolated from baseline")
    old=jsonfile(baseline/"song.hsicert")
    require(old["closed"]==1 and old["technical_closed"]==1 and old["correspondence_closed"]==1,
            "baseline lacks technical and correspondence closure")
    base_hash=sha(baseline/"song.wav")
    require(old["audio_sha256"]==base_hash,"baseline WAV SHA256 does not match certificate")
    base_events=old["event_count"]
    base_sources={x["source_id"] for x in jsonfile(baseline/"events.json")}
    keywords=" ".join(a.keywords)
    require(0<=a.start<len(PROPOSALS),"start outside finite proposal domain")
    require(1<=a.max_candidates<=len(PROPOSALS),"max-candidates outside finite domain")
    require(a.start<a.max_candidates,"no candidates in requested range")
    attempted=[]
    selected=None
    for i in range(a.start,a.max_candidates):
        cfg={"protocol":POLICY_PROTOCOL,**PROPOSALS[i]}
        sub=root/("candidate-%03d"%i);sub.mkdir(parents=True,exist_ok=True)
        path=sub/"render-policy.json"
        path.write_text(canon(cfg)+"\n",encoding="utf-8")
        env=os.environ.copy()
        env.update(HSI_RENDER_PROFILE=str(path),
                   HSI_RC_MAX_CANDIDATES="1",
                   HSI_CORRESPONDENCE="1")
        # Never permit an acceptance bypass using environment overrides.
        for k in list(env):
            if k.startswith("HSI_RC_") and k not in ("HSI_RC_MAX_CANDIDATES",):
                env.pop(k,None)
        r=subprocess.run(
            [sys.executable,str(ROOT/"hsi_open_corpus.py"),"--lock",str(Path(a.lock).resolve()),
             "--out",str(sub),keywords],env=env,capture_output=True,text=True,timeout=180)
        if r.returncode!=0:
            attempted.append({"index":i,"status":"HOLD","reason":"renderer rejected candidate"})
            continue
        v=subprocess.run([sys.executable,str(ROOT/"hsi_corpus_clxy_gate.py"),
                         "--artifact",str(sub),"--expected-policy",str(path)],
                         env=env,capture_output=True,text=True,timeout=60)
        if v.returncode!=0:
            attempted.append({"index":i,"status":"HOLD","reason":"CLXY/WAV verification failed",
                              "details":v.stderr[-300:]})
            continue
        now=jsonfile(sub/"song.hsicert")
        event_ids={x["source_id"] for x in jsonfile(sub/"events.json")}
        structural=now["event_count"]>base_events and len(event_ids)>=len(base_sources)
        different=sha(sub/"song.wav")!=base_hash
        if not (structural and different):
            attempted.append({"index":i,"status":"HOLD","reason":"no measurable structural improvement"})
            continue
        attempted.append({"index":i,"status":"VERIFIED","event_count":now["event_count"]})
        selected=(i,cfg,now,sub,jsonfile(sub/"deployment.clxycert"))
        break
    if selected is None:
        checkpoint={"protocol":PROTOCOL,"status":"HOLD","closed":0,
                    "start":a.start,"next_candidate":a.max_candidates,"attempts":attempted,
                    "reason":"no candidate with verified correspondence and measurable structure improvement"}
        (root/"evolution.state.json").write_text(canon(checkpoint)+"\n",encoding="utf-8")
        print(canon(checkpoint))
        raise SystemExit(3)
    i,cfg,now,sub,gate=selected
    acceptance={
        "protocol":PROTOCOL,"status":"VERIFIED_PROPOSAL","closed":1,
        "candidate_index":i,"policy":cfg,
        "baseline":{"audio_sha256":base_hash,"events":base_events,"unique_sources":len(base_sources)},
        "candidate":{"audio_sha256":now["audio_sha256"],"events":now["event_count"],
                     "unique_sources":len({x["source_id"] for x in jsonfile(sub/"events.json")}),
                     "correspondence_residual":now["correspondence"]["residual"],
                     "render_policy_uid":now["render_policy_uid"]},
        "proof":{"clxy_status":gate["status"],"clxy_step_D1_num":gate["clxy"]["step_D1_num"],
                 "clxy_evolve_D1_num":gate["clxy"]["evolve_D1_num"],
                 "wav_correspondence_closed":gate["artifact"]["correspondence_closed"]},
        "attempts":attempted,
        "scope":"audited bounded DSP-parameter proposal, not automatic arbitrary Python code synthesis",
        "git_commit_performed":False,
        "publication_rights_automatically_cleared":False
    }
    (root/"hsi_render_policy.json").write_text(canon(cfg)+"\n",encoding="utf-8")
    (root/"hsi_corpus_evolution.hsicert").write_text(canon(acceptance)+"\n",encoding="utf-8")
    print(canon(acceptance))

if __name__=="__main__":
    try:main()
    except (ValueError,OSError,KeyError,TypeError,subprocess.TimeoutExpired) as e:
        print(canon({"protocol":PROTOCOL,"status":"HOLD","closed":0,"reason":str(e)}),file=sys.stderr)
        raise SystemExit(3)
