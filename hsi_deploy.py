#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, py_compile, shutil, stat, sys, tempfile, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path
from hsi_net import projection_request, projection_certificate, VERSION as HSI_NET_VERSION

PROTOCOL="HSI-DEPLOY/1.0"
VERSION="1.0.0"
BLUE_PROTOCOL="HSI-PLEIADIAN-BLUE-CARE/1.0"
USER_AGENT="HSI-DEPLOY/1.0 (https://github.com/letsgo0226/Notes)"
MAX_FILE_BYTES=4*1024*1024

if hasattr(sys,"set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

def e257(data: bytes) -> int:
    n=1
    for b in data:n=n*257+b+1
    return n

def canon(x) -> str:
    return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":"))

TARGETS={
    "self":{
        "label":"HSI_CORE",
        "repo":"letsgo0226/Notes",
        "ref":"main",
        "files":{
            "hsi_net.py":"hsi_net.py",
            "hsi_search.py":"hsi_search.py",
            "hsi_open_corpus.py":"hsi_open_corpus.py",
            "hsi_native_renderer.py":"hsi_native_renderer.py",
            "hsi_update.py":"hsi_update.py",
            "hsi_deploy.py":"hsi_deploy.py"
        }
    },
    "utm":{
        "label":"UTM",
        "repo":"letsgo0226/UTM.sh",
        "ref":"hsi-three-system-v1",
        "files":{
            "hsi_common/core.py":"core.py",
            "hsi_blue_native.py":"hsi_blue_native.py"
        }
    },
    "trader_42":{
        "label":"TRADER_42",
        "repo":"letsgo0226/Trader_42.sh",
        "ref":"hsi-three-system-v1",
        "auth_required":True,
        "files":{
            "hsi_common/core.py":"core.py",
            "hsi_blue_native.py":"hsi_blue_native.py"
        }
    },
    "omega":{
        "label":"OMEGA",
        "repo":"letsgo0226/COSMIC_LOVE_IS_THE_SOLUTIONS_FOR_EVERYTHING_HS_ZERO.sh",
        "ref":"hsi-three-system-v1",
        "files":{
            "hsi_common/core.py":"core.py",
            "hsi_blue_native.py":"hsi_blue_native.py"
        }
    }
}

ALIASES={
    "core":"self","hsi":"self","self":"self",
    "utm":"utm",
    "trader":"trader_42","trader42":"trader_42","trader_42":"trader_42",
    "omega":"omega","cosmic_love":"omega","cosmic-love":"omega",
    "all":"all"
}

def _github_token():
    return (os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN") or "").strip()

def _http_bytes(url,timeout=30):
    headers={"User-Agent":USER_AGENT,"Accept":"application/vnd.github+json,*/*"}
    token=_github_token()
    if token and (url.startswith("https://api.github.com/") or url.startswith("https://raw.githubusercontent.com/")):
        headers["Authorization"]="Bearer "+token
    req=urllib.request.Request(url,headers=headers)
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r:
            data=r.read(MAX_FILE_BYTES+1)
            if len(data)>MAX_FILE_BYTES:
                raise RuntimeError("source file exceeds deployment byte budget")
            return data
    except urllib.error.HTTPError as e:
        body=e.read().decode("utf-8","replace")
        raise RuntimeError("HTTP %s: %s"%(e.code,body[:300])) from None
    except urllib.error.URLError as e:
        raise RuntimeError("source unavailable: %s"%getattr(e,"reason",e)) from None

def _http_json(url,timeout=30):
    return json.loads(_http_bytes(url,timeout).decode("utf-8"))

def resolve_commit(repo,ref):
    owner,name=repo.split("/",1)
    owner_q=urllib.parse.quote(owner,safe="")
    name_q=urllib.parse.quote(name,safe="")
    ref_q=urllib.parse.quote(ref,safe="")
    candidates=[
        ("branch","https://api.github.com/repos/%s/%s/branches/%s"%(owner_q,name_q,ref_q)),
        ("git_ref","https://api.github.com/repos/%s/%s/git/ref/heads/%s"%(owner_q,name_q,ref_q)),
        ("commit","https://api.github.com/repos/%s/%s/commits/%s"%(owner_q,name_q,ref_q))
    ]
    errors=[]
    for method,url in candidates:
        try:
            data=_http_json(url)
            if method=="branch":
                sha=((data.get("commit") or {}).get("sha") or "").strip()
            elif method=="git_ref":
                sha=((data.get("object") or {}).get("sha") or "").strip()
            else:
                sha=(data.get("sha") or "").strip()
            if len(sha)==40 and all(c in "0123456789abcdefABCDEF" for c in sha):
                return sha.lower(),url,method
            errors.append(method+":invalid_sha")
        except Exception as e:
            errors.append(method+":"+str(e))
    raise RuntimeError("cannot resolve %s@%s within finite resolver set: %s"%(repo,ref," | ".join(errors)))

def raw_url(repo,commit,path):
    return "https://raw.githubusercontent.com/%s/%s/%s"%(repo,commit,urllib.parse.quote(path,safe="/"))

def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()

def git_blob_sha1(data):
    header=("blob %d\0"%len(data)).encode("ascii")
    return hashlib.sha1(header+data).hexdigest()

def _contains(text,*markers):
    return all(m in text for m in markers)

def validate_target(name,root):
    checks={}
    def read(rel):
        return (root/rel).read_text(encoding="utf-8")
    for p in root.rglob("*.py"):
        try:
            py_compile.compile(str(p),doraise=True)
            checks["py_compile:"+p.name]=True
        except Exception:
            checks["py_compile:"+p.name]=False

    if name=="self":
        net=read("hsi_net.py")
        search=read("hsi_search.py")
        corpus=read("hsi_open_corpus.py")
        native=read("hsi_native_renderer.py")
        deploy=read("hsi_deploy.py")
        checks.update({
            "deploy_protocol":'PROTOCOL="HSI-DEPLOY/1.0"' in deploy,
            "net_formal_only":'FORMAL_INFORMATION_MODEL_ONLY' in net,
            "net_github_adapter":'"github_source"' in net,
            "search_semantic_humility":'absence_of_retrieval_is_not_evidence_of_nonexistence' in search,
            "corpus_no_ai":_contains(corpus,'"ai_model":False','"neural_renderer":False','"machine_learning":False'),
            "native_protocol":'PROTOCOL="HSI-NATIVE-FIELD/1.0"' in native,
            "update_protocol":'PROTOCOL="HSI-UPDATE/1.0"' in read("hsi_update.py"),
            "update_no_auto_rewrite":'"automatic_source_code_rewrite":False' in read("hsi_update.py"),
            "update_no_auto_push":'"automatic_git_push":False' in read("hsi_update.py")
        })
    else:
        core=read("core.py")
        app=read("hsi_blue_native.py")
        checks["shared_core_protocol"]='PROTOCOL = "HSI-3SYS/1.0"' in core
        checks["forbidden_universal_claims"]="halting_decider" in core and "profit_guarantee" in core
        checks["blue_semantic_humility"]='"semantic_non_coercion":True' in app and '"forced_totalization":False' in app
        checks["search_cannot_authorize_domain_action"]='"may_authorize_domain_action":False' in app
        if name=="utm":
            checks["utm_identity"]='SYSTEM="UTM"' in app
            checks["utm_no_universal_solver"]='"solver_may_claim_universal_solution":False' in app
            checks["utm_no_nonhalting_from_search"]='"may_decide_nonhalting":False' in app
        elif name=="trader_42":
            checks["trader_identity"]='SYSTEM="TRADER_42"' in app
            checks["trader_certificate_only"]='"execution_mode":"CERTIFICATE_ONLY"' in app
            checks["trader_dry_run"]='"dry_run":True' in app
            checks["trader_unarmed"]='"live_armed":False' in app
            checks["trader_no_credentials"]='"credentials_used":False' in app
            checks["trader_no_order_submission"]='"order_submission":False' in app
            checks["trader_search_no_authority"]='"may_authorize_trade":False' in app
        elif name=="omega":
            checks["omega_identity"]='SYSTEM="OMEGA"' in app
            checks["omega_no_forced_commit"]='"may_force_commit":False' in app
    return checks

def choose_targets(raw):
    if not raw:
        return list(TARGETS)
    out=[]
    for token in raw:
        for part in token.split(","):
            key=ALIASES.get(part.strip().lower())
            if not key:
                raise SystemExit("unknown target: "+part)
            if key=="all":
                return list(TARGETS)
            if key not in out:out.append(key)
    return out

def observe_environment(root,targets):
    py_ok=sys.version_info>=(3,9)
    parent=root.parent
    parent.mkdir(parents=True,exist_ok=True)
    writable=os.access(str(parent),os.W_OK)
    return {
        "python_version":"%d.%d.%d"%sys.version_info[:3],
        "python_ok":py_ok,
        "platform":sys.platform,
        "install_root":str(root),
        "install_parent_writable":bool(writable),
        "targets":targets,
        "live_trading_authorized":False,
        "autonomous_domain_action_authorized":False,
        "github_auth_available":bool(_github_token())
    }

def solve_plan(root,targets):
    env=observe_environment(root,targets)
    observations=[]
    sources={}
    status="DEPLOYABLE"
    reason=None
    if not env["python_ok"]:
        status="BLOCKED";reason="python_3_9_or_newer_required"
    elif not env["install_parent_writable"]:
        status="BLOCKED";reason="install_parent_not_writable"
    if status=="DEPLOYABLE":
        for name in targets:
            spec=TARGETS[name]
            if spec.get("auth_required") and not _github_token():
                observations.append({
                    "target":name,"repo":spec["repo"],"ref":spec["ref"],
                    "status":"AUTH_REQUIRED",
                    "reason":"private_repository_requires_GITHUB_TOKEN_or_GH_TOKEN"
                })
                status="UNRESOLVED";reason="private_source_auth_required";break
            try:
                commit,url,method=resolve_commit(spec["repo"],spec["ref"])
                sources[name]={"repo":spec["repo"],"ref":spec["ref"],"commit":commit,"resolver_url":url,"resolver_method":method,"files":spec["files"]}
                observations.append({"target":name,"repo":spec["repo"],"ref":spec["ref"],"commit":commit,"resolver_method":method,"status":"RESOLVED"})
            except Exception as e:
                observations.append({"target":name,"repo":spec["repo"],"ref":spec["ref"],"status":"SOURCE_UNAVAILABLE","error":str(e)})
                status="UNRESOLVED";reason="source_resolution_failed";break

    net_req=projection_request(
        "Resolve immutable software sources for HSI self-deployment and three-system deployment",
        ["github_source"],
        {
            "targets":targets,
            "commit_pinning_required":True,
            "trader_live_authority":False,
            "forced_totalization":False
        },
        {"repositories":len(targets),"max_files":sum(len(TARGETS[x]["files"]) for x in targets)}
    )
    net_cert=projection_certificate(net_req,observations,status)
    base={
        "protocol":PROTOCOL,"version":VERSION,
        "request":{"targets":targets,"root":str(root)},
        "environment":env,
        "sources":sources,
        "status":status,
        "reason":reason,
        "operations":["OBSERVE","RESOLVE","VERIFY","COMMIT_OR_HOLD"],
        "net_projection":net_cert,
        "invariants":{
            "immutable_commit_resolution_required":True,
            "partial_source_resolution_never_commits":True,
            "private_source_without_auth_never_commits":True,
            "credentials_are_never_written_to_certificates":True,
            "verification_failure_never_commits":True,
            "deployment_does_not_imply_domain_execution":True,
            "trader_live_authority":False,
            "trader_order_submission":False,
            "utm_universal_halting_authority":False,
            "omega_forced_commit_authority":False
        },
        "blue":{
            "protocol":BLUE_PROTOCOL,
            "semantic_non_coercion":True,
            "semantic_humility":True,
            "human_invocation":True,
            "forced_totalization":False
        }
    }
    base["plan_uid"]=str(e257(canon(base).encode("utf-8")))
    return base

def download_target(name,spec,resolved,stage):
    tdir=stage/name
    tdir.mkdir(parents=True,exist_ok=True)
    records=[]
    for remote,local in spec["files"].items():
        url=raw_url(spec["repo"],resolved["commit"],remote)
        data=_http_bytes(url,timeout=60)
        if not data:
            raise RuntimeError("empty source file: "+remote)
        p=tdir/local
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(data)
        records.append({
            "remote_path":remote,"local_path":local,"url":url,
            "bytes":len(data),"sha256":sha256_bytes(data),"git_blob_sha1":git_blob_sha1(data)
        })
    checks=validate_target(name,tdir)
    if not all(checks.values()):
        bad=[k for k,v in checks.items() if not v]
        raise RuntimeError("verification failed: "+",".join(bad))
    return tdir,records,checks

def _write_atomic(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+".tmp.%d"%os.getpid())
    tmp.write_text(text,encoding="utf-8")
    os.replace(str(tmp),str(path))

def make_dispatcher(root,current):
    script=f'''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
ROOT=Path({str(root)!r})
STATE=json.loads((ROOT/"current.json").read_text(encoding="utf-8"))
TARGETS=STATE["targets"]
ALIASES={{"deploy":("self","hsi_deploy.py"),"net":("self","hsi_net.py"),"search":("self","hsi_search.py"),
         "corpus":("self","hsi_open_corpus.py"),"native":("self","hsi_native_renderer.py"),
         "update":("self","hsi_update.py"),
         "utm":("utm","hsi_blue_native.py"),"trader":("trader_42","hsi_blue_native.py"),
         "trader_42":("trader_42","hsi_blue_native.py"),"omega":("omega","hsi_blue_native.py")}}
if len(sys.argv)<2 or sys.argv[1] not in ALIASES:
    raise SystemExit("usage: hsi.py deploy|net|search|corpus|native|update|utm|trader|omega [args...]")
target,file=ALIASES[sys.argv[1]]
if target not in TARGETS:
    raise SystemExit("target not deployed: "+target)
path=Path(TARGETS[target])/file
os.execv(sys.executable,[sys.executable,str(path)]+sys.argv[2:])
'''
    _write_atomic(root/"hsi.py",script)
    try:
        (root/"hsi.py").chmod((root/"hsi.py").stat().st_mode|stat.S_IXUSR)
    except Exception:pass
    shell='#!/bin/sh\nexec python3 "%s" "$@"\n'%str(root/"hsi.py")
    _write_atomic(root/"hsi",shell)
    try:(root/"hsi").chmod(0o700)
    except Exception:pass
    cmd='@echo off\r\npy -3 "%s" %%*\r\n'%str(root/"hsi.py")
    _write_atomic(root/"hsi.cmd",cmd)

def commit_plan(plan,root):
    if plan["status"]!="DEPLOYABLE":
        return None,{"status":"HOLD","reason":plan.get("reason")}
    release_id=time.strftime("%Y%m%d-%H%M%S")+"-"+hashlib.sha256(canon(plan).encode()).hexdigest()[:12]
    releases=root/"releases"
    final=releases/release_id
    if final.exists():
        raise RuntimeError("release path already exists")
    stage=Path(tempfile.mkdtemp(prefix=".hsi-deploy-",dir=str(root.parent)))
    results={}
    try:
        payload=stage/"release"
        payload.mkdir(parents=True,exist_ok=True)
        for name in plan["request"]["targets"]:
            tdir,records,checks=download_target(name,TARGETS[name],plan["sources"][name],payload)
            results[name]={
                "label":TARGETS[name]["label"],
                "repo":plan["sources"][name]["repo"],
                "ref":plan["sources"][name]["ref"],
                "commit":plan["sources"][name]["commit"],
                "files":records,
                "checks":checks,
                "status":"VERIFIED"
            }
        releases.mkdir(parents=True,exist_ok=True)
        shutil.move(str(payload),str(final))
    finally:
        shutil.rmtree(stage,ignore_errors=True)

    current={
        "protocol":PROTOCOL,
        "release_id":release_id,
        "release_dir":str(final),
        "targets":{name:str(final/name) for name in results},
        "deployed_at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
    }
    _write_atomic(root/"current.json",canon(current)+"\n")
    make_dispatcher(root,current)
    return current,results

def make_certificate(plan,current,results,plan_only=False,error=None):
    committed=bool(current) and not plan_only and error is None
    status="COMMITTED" if committed else ("PLAN" if plan_only and plan["status"]=="DEPLOYABLE" else "HOLD")
    cert={
        "protocol":PROTOCOL,"version":VERSION,
        "plan_uid":plan["plan_uid"],
        "status":status,
        "plan_status":plan["status"],
        "request":plan["request"],
        "environment":plan["environment"],
        "net_projection":plan["net_projection"],
        "invariants":plan["invariants"],
        "blue":plan["blue"],
        "release":current,
        "targets":results or {},
        "error":error,
        "closure":{
            "plan_resolved":plan["status"]=="DEPLOYABLE",
            "all_targets_verified":bool(results) and all(x.get("status")=="VERIFIED" for x in results.values()) if committed else False,
            "committed":committed,
            "domain_execution_performed":False,
            "trader_live_armed":False,
            "trader_order_submission":False
        }
    }
    cert["certificate_uid"]=str(e257(canon(cert).encode("utf-8")))
    cert["closed"]=1 if committed or (plan_only and plan["status"]=="DEPLOYABLE") else 0
    return cert

def main():
    ap=argparse.ArgumentParser(description="HSI self-deployment solver and three-system deployment gate")
    ap.add_argument("--target",action="append",default=[],help="self, utm, trader_42, omega, all (repeatable/comma-separated)")
    ap.add_argument("--root",default=os.getenv("HSI_HOME",str(Path.home()/".hsi")))
    ap.add_argument("--plan",action="store_true",help="solve and verify source resolution without writing deployment files")
    ap.add_argument("--json",action="store_true")
    a=ap.parse_args()
    targets=choose_targets(a.target)
    root=Path(a.root).expanduser()
    plan=solve_plan(root,targets)
    print("protocol>",PROTOCOL)
    print("plan_uid>",plan["plan_uid"])
    print("targets>",",".join(targets))
    print("plan_status>",plan["status"])
    current=None;results={};error=None
    if a.plan:
        cert=make_certificate(plan,None,{},plan_only=True)
    elif plan["status"]!="DEPLOYABLE":
        cert=make_certificate(plan,None,{})
    else:
        root.mkdir(parents=True,exist_ok=True)
        try:
            current,results=commit_plan(plan,root)
            cert=make_certificate(plan,current,results)
        except Exception as e:
            error=str(e)
            cert=make_certificate(plan,None,results,error=error)
    state_dir=root/"state"/"deployments"
    state_dir.mkdir(parents=True,exist_ok=True)
    stamp=time.strftime("%Y%m%d-%H%M%S")
    cert_path=state_dir/(stamp+"-"+hashlib.sha256(cert["certificate_uid"].encode()).hexdigest()[:10]+".hsicert")
    lock_path=state_dir/(stamp+"-"+hashlib.sha256(cert["plan_uid"].encode()).hexdigest()[:10]+".lock.json")
    _write_atomic(cert_path,canon(cert)+"\n")
    _write_atomic(lock_path,canon(plan)+"\n")
    print("status>",cert["status"])
    print("certificate>",cert_path)
    print("lock>",lock_path)
    if current:
        print("release>",current["release_dir"])
        print("launcher>",root/"hsi.py")
        print("invoke> python3 %s <net|search|corpus|native|utm|trader|omega>"%(root/"hsi.py"))
    if error:print("error>",error,file=sys.stderr)
    if a.json:print(canon(cert))
    raise SystemExit(0 if cert["closed"] else 3)

if __name__=="__main__":
    main()
