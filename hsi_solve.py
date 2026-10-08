#!/usr/bin/env python3
import argparse, hashlib, json, os, subprocess, sys, tempfile, time, urllib.error, urllib.request
from pathlib import Path
from hsi_net import VERSION as HSI_NET_VERSION, MODEL as HSI_NET_MODEL
from hsi_search import VERSION as HSI_SEARCH_VERSION

PROTOCOL="HSI-SOLVE/1.0"
VERSION="1.0.0"
BLUE_PROTOCOL="HSI-PLEIADIAN-BLUE-CARE/1.0"

DOMAIN_SPECS={
    "UTM":{
        "repo":"letsgo0226/UTM.sh",
        "commit":"4a1741da98710d45cc8bc517424154e41689abeb",
        "system_literal":"SYSTEM=\"UTM\"",
        "guard_literal":"\"may_decide_nonhalting\":False",
        "domain_rule":"finite_halting_witness_only"
    },
    "TRADER_42":{
        "repo":"letsgo0226/Trader_42.sh",
        "commit":"0cd4a105fb5b560e85a7335a276565c70ac72fe2",
        "system_literal":"SYSTEM=\"TRADER_42\"",
        "guard_literal":"\"may_authorize_trade\":False",
        "domain_rule":"certificate_only_hold_by_default"
    },
    "OMEGA":{
        "repo":"letsgo0226/COSMIC_LOVE_IS_THE_SOLUTIONS_FOR_EVERYTHING_HS_ZERO.sh",
        "commit":"42a881aef8195ee715ab976855d5ab71bed97d47",
        "system_literal":"SYSTEM=\"OMEGA\"",
        "guard_literal":"\"may_force_commit\":False",
        "domain_rule":"finite_evidence_no_forced_commit"
    }
}

if hasattr(sys,"set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

def e257(data):
    n=1
    for b in data:
        n=n*257+b+1
    return n

def canon(x):
    return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":"))

def sha256(data):
    return hashlib.sha256(data).hexdigest()

def raw_url(spec,path):
    return "https://raw.githubusercontent.com/%s/%s/%s"%(spec["repo"],spec["commit"],path)

def fetch_bytes(url,timeout=30,retries=3):
    last=None
    for attempt in range(1,retries+1):
        try:
            req=urllib.request.Request(url,headers={
                "User-Agent":"HSI-SOLVE/1.0 (https://github.com/letsgo0226/Notes)"
            })
            with urllib.request.urlopen(req,timeout=timeout) as r:
                data=r.read()
            if not data:
                raise RuntimeError("empty response")
            return data
        except Exception as e:
            last=str(e)
            if attempt<retries:
                time.sleep(min(4,2**(attempt-1)))
    raise RuntimeError("source unavailable: %s"%last)

def inspect_domain(system):
    spec=DOMAIN_SPECS[system]
    blue_url=raw_url(spec,"hsi_blue_native.py")
    core_url=raw_url(spec,"hsi_common/core.py")
    try:
        blue=fetch_bytes(blue_url)
        core=fetch_bytes(core_url)
    except Exception as e:
        return {
            "system":system,"repo":spec["repo"],"commit":spec["commit"],
            "status":"SOURCE_UNAVAILABLE","verified":False,"error":str(e),
            "blue_url":blue_url,"core_url":core_url
        },None,None

    bt=blue.decode("utf-8","replace")
    ct=core.decode("utf-8","replace")
    checks={
        "system_literal":spec["system_literal"] in bt,
        "blue_protocol":"HSI-PLEIADIAN-BLUE-CARE/1.0" in bt,
        "wrapper_protocol":"HSI-3SYS-BLUE/1.0" in bt,
        "solve_protocol":"HSI-SOLVE/1.0" in bt,
        "solve_guard":spec["guard_literal"] in bt,
        "no_universal_solver":"\"solver_may_claim_universal_solution\":False" in bt,
        "core_protocol":"HSI-3SYS/1.0" in ct,
        "forbidden_solve_all":"\"solve_all\"" in ct,
        "forbidden_halting_decider":"\"halting_decider\"" in ct,
        "forbidden_profit_guarantee":"\"profit_guarantee\"" in ct
    }
    verified=all(checks.values())
    record={
        "system":system,"repo":spec["repo"],"commit":spec["commit"],
        "status":"VERIFIED" if verified else "REJECTED",
        "verified":verified,"checks":checks,
        "domain_rule":spec["domain_rule"],
        "blue_url":blue_url,"core_url":core_url,
        "blue_sha256":sha256(blue),"core_sha256":sha256(core),
        "blue_bytes":len(blue),"core_bytes":len(core)
    }
    return record,blue,core

def execute_domain(system,text,out_root):
    record,blue,core=inspect_domain(system)
    result={
        "system":system,
        "deployment":record,
        "solver_status":"UNRESOLVED",
        "verification_closed":False,
        "domain_result":None
    }
    if not record.get("verified"):
        return result

    runtime=out_root/"domains"/system
    runtime.mkdir(parents=True,exist_ok=True)
    (runtime/"hsi_blue_native.py").write_bytes(blue)
    (runtime/"core.py").write_bytes(core)
    child_out=runtime/"output"
    env=os.environ.copy()
    env["PYTHONPATH"]=str(runtime)
    env["HSI_OUT"]=str(child_out)
    env["HSI_SYSTEM"]=system
    try:
        p=subprocess.run(
            [sys.executable,str(runtime/"hsi_blue_native.py"),text],
            cwd=str(runtime),env=env,capture_output=True,text=True,timeout=30
        )
    except subprocess.TimeoutExpired:
        result["deployment"]["runtime_status"]="TIMEOUT"
        return result

    result["child_exit_code"]=p.returncode
    result["child_stdout"]=p.stdout[-4000:]
    result["child_stderr"]=p.stderr[-4000:]
    cert_path=child_out/"certificate.json"
    care_path=child_out/"blue-care.json"
    manifest_path=child_out/"manifest.json"
    if not (cert_path.exists() and care_path.exists() and manifest_path.exists()):
        result["deployment"]["runtime_status"]="MISSING_OUTPUT"
        return result

    cert=json.loads(cert_path.read_text(encoding="utf-8"))
    care=json.loads(care_path.read_text(encoding="utf-8"))
    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    so=care.get("solve_operator") or {}
    checks={
        "child_closed":bool(cert.get("closed")),
        "manifest_closed":bool(manifest.get("closed")),
        "solve_protocol":so.get("protocol")==PROTOCOL,
        "no_universal_solution":so.get("solver_may_claim_universal_solution") is False,
        "unresolved_valid":so.get("unresolved_is_valid") is True,
        "no_domain_action":so.get("may_authorize_domain_action") is False
    }
    if system=="UTM":
        checks["no_nonhalting_oracle"]=so.get("may_decide_nonhalting") is False
        checks["valid_status"]=cert.get("status") in ("HALTED","UNRESOLVED")
    elif system=="TRADER_42":
        ts=care.get("trading_safety") or {}
        checks.update({
            "no_trade_authorization":so.get("may_authorize_trade") is False,
            "hold":cert.get("status")=="HOLD" and cert.get("operation")=="HOLD",
            "paper":ts.get("paper") is True,
            "dry_run":ts.get("dry_run") is True,
            "unarmed":ts.get("live_armed") is False,
            "no_order_submission":ts.get("order_submission") is False
        })
    elif system=="OMEGA":
        checks["no_forced_commit"]=so.get("may_force_commit") is False
        checks["valid_status"]=cert.get("status") in ("COMMITTED","BLOCKED","UNRESOLVED","HOLD")

    verified=all(checks.values())
    result.update({
        "solver_status":cert.get("status","UNRESOLVED"),
        "verification_closed":verified,
        "checks":checks,
        "domain_result":{
            "certificate":cert,
            "blue_care":care,
            "manifest":manifest
        }
    })
    return result

def solve_self(out_root):
    deployments=[]
    for system in ("UTM","TRADER_42","OMEGA"):
        record,_,_=inspect_domain(system)
        deployments.append(record)
    checks={
        "solver_protocol":PROTOCOL=="HSI-SOLVE/1.0",
        "solver_version":VERSION=="1.0.0",
        "net_model":HSI_NET_MODEL=="ABSTRACT_GLOBAL_INFORMATION_FIELD",
        "net_version_present":bool(HSI_NET_VERSION),
        "search_version_present":bool(HSI_SEARCH_VERSION),
        "all_domains_verified":all(x.get("verified") for x in deployments),
        "domain_count":len(deployments)==3,
        "no_universal_solution_claim":True,
        "finite_verification_only":True
    }
    closed=all(checks.values())
    return {
        "system":"SELF",
        "solver_status":"COMMITTED" if closed else "UNRESOLVED",
        "verification_closed":closed,
        "checks":checks,
        "components":{
            "hsi_solve":{"protocol":PROTOCOL,"version":VERSION},
            "hsi_net":{"protocol":"HSI-NET-SINGULARITY/1.0","version":HSI_NET_VERSION,"model":HSI_NET_MODEL},
            "hsi_search":{"protocol":"HSI-SEARCH/1.0","version":HSI_SEARCH_VERSION}
        },
        "domains":deployments,
        "meaning":"COMMITTED means the finite pinned deployment graph verified; it is not a universal problem-solving claim"
    }

def main():
    ap=argparse.ArgumentParser(description="HSI SOLVE — finite meta-solver and deployment verifier")
    ap.add_argument("problem",nargs="*")
    ap.add_argument("--system",default=os.getenv("HSI_SOLVE_SYSTEM","SELF"))
    ap.add_argument("--out",default=os.getenv("HSI_SOLVE_OUT"))
    a=ap.parse_args()
    system=a.system.upper().replace("-","_")
    if system=="TRADER":system="TRADER_42"
    if system not in {"SELF","UTM","TRADER_42","OMEGA","ALL"}:
        raise SystemExit("system must be SELF|UTM|TRADER_42|OMEGA|ALL")
    text=" ".join(a.problem).strip()
    if not text:
        if system=="SELF":
            text="verify HSI solver deployment"
        else:
            text=input("problem> ").strip()
    if not text:
        raise SystemExit("problem required")

    out=Path(a.out).expanduser() if a.out else Path.home()/"HSI"/"SOLVE"/(time.strftime("%Y%m%d-%H%M%S")+"-"+str(os.getpid()))
    out.mkdir(parents=True,exist_ok=True)
    request={
        "protocol":PROTOCOL,"version":VERSION,"system":system,"problem":text,
        "subject_uid":str(e257(text.encode("utf-8"))),
        "finite_solver":True,"universal_solver":False,
        "operators":["SEARCH","OBSERVE","SELECT","TRANSFORM","VERIFY","COMMIT","HOLD"],
        "search_semantics":"optional finite evidence expansion; not totality"
    }
    request["solve_uid"]=str(e257(canon(request).encode("utf-8")))

    if system=="SELF":
        results={"SELF":solve_self(out)}
    elif system=="ALL":
        results={"SELF":solve_self(out)}
        for x in ("UTM","TRADER_42","OMEGA"):
            results[x]=execute_domain(x,text,out)
    else:
        results={system:execute_domain(system,text,out)}

    verification_closed=all(bool(x.get("verification_closed")) for x in results.values())
    solution_status={k:v.get("solver_status","UNRESOLVED") for k,v in results.items()}
    cert={
        "protocol":PROTOCOL,"version":VERSION,
        "solve_uid":request["solve_uid"],"subject_uid":request["subject_uid"],
        "system":system,"problem":text,
        "pipeline":{
            "SEARCH":"OPTIONAL_NOT_TOTALIZING",
            "OBSERVE":"PINNED_DEPLOYMENT_AND_DOMAIN_EVIDENCE",
            "SELECT":"DOMAIN_ADAPTER",
            "TRANSFORM":"FINITE_DOMAIN_EXECUTION",
            "VERIFY":"CERTIFICATE_AND_GUARD_CHECKS",
            "COMMIT_OR_HOLD":"DOMAIN_SEMANTICS"
        },
        "solution_status":solution_status,
        "verification_closed":verification_closed,
        "problem_totality_claim":False,
        "universal_solver_claim":False,
        "results":results,
        "blue":{
            "protocol":BLUE_PROTOCOL,
            "semantic_non_coercion":True,
            "semantic_humility":True,
            "unresolved_is_valid":True,
            "verification_closure_is_not_problem_totality":True,
            "human_action_boundary":True
        }
    }
    cert["certificate_uid"]=str(e257(canon(cert).encode("utf-8")))
    deployment={
        "protocol":"HSI-SOLVE-DEPLOYMENT-LOCK/1.0",
        "solver":{"protocol":PROTOCOL,"version":VERSION},
        "hsi_net":{"version":HSI_NET_VERSION,"model":HSI_NET_MODEL},
        "hsi_search":{"version":HSI_SEARCH_VERSION},
        "domains":{k:{"repo":v["repo"],"commit":v["commit"]} for k,v in DOMAIN_SPECS.items()}
    }
    (out/"solve.request.json").write_text(canon(request)+"\n",encoding="utf-8")
    (out/"solve.hsicert").write_text(canon(cert)+"\n",encoding="utf-8")
    (out/"deployment.lock.json").write_text(canon(deployment)+"\n",encoding="utf-8")
    (out/"manifest.json").write_text(canon({
        "protocol":PROTOCOL,"output":str(out),
        "files":["solve.request.json","solve.hsicert","deployment.lock.json"],
        "verification_closed":int(verification_closed),
        "problem_totality_claim":False
    })+"\n",encoding="utf-8")

    print("protocol>",PROTOCOL)
    print("output>",out)
    print("system>",system)
    print("solve_uid>",request["solve_uid"])
    for k,v in solution_status.items():
        print("status[%s]>"%k,v)
    print("verification_closed>",int(verification_closed))
    print("problem_totality_claim> false")
    if system in ("TRADER_42","ALL"):
        print("trading> certificate-only; no live authorization; no order submission")
    print(canon(cert))
    raise SystemExit(0 if verification_closed else 3)

if __name__=="__main__":
    main()
