#!/usr/bin/env python3
import json, sys

PROTOCOL="HSI-NET-SINGULARITY/1.0"
VERSION="1.1.0"
MODEL="ABSTRACT_GLOBAL_INFORMATION_FIELD"
BLUE_PROTOCOL="HSI-PLEIADIAN-BLUE-CARE/1.0"

if hasattr(sys,"set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

def e257(data):
    n=1
    for b in data:
        n=n*257+b+1
    return n

def canon(x):
    return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":"))

ADAPTERS={
    "openverse_audio":{
        "adapter_protocol":"HSI-ADAPTER-OPENVERSE-AUDIO/1.0",
        "status":"ACTIVE",
        "medium":"audio",
        "scope":"openly-licensed/public-domain media indexed by Openverse",
        "authority":"Openverse API",
        "exhaustive":False,
        "rights_boundary":"caller policy + source provenance + independent rights review where needed"
    },
    "wikimedia_commons_audio":{
        "adapter_protocol":"HSI-ADAPTER-WIKIMEDIA-COMMONS-AUDIO/1.0",
        "status":"ACTIVE",
        "medium":"audio",
        "scope":"audio files and machine-readable rights metadata exposed by Wikimedia Commons",
        "authority":"Wikimedia Commons Action API",
        "exhaustive":False,
        "rights_boundary":"Commons extmetadata + caller policy + independent rights review where needed"
    },
    "network_audio":{
        "adapter_protocol":"HSI-ADAPTER-NETWORK-AUDIO-UNION/1.0",
        "status":"ACTIVE",
        "medium":"audio",
        "scope":"finite union projection over registered public audio adapters",
        "authority":"HSI NET adapter union",
        "members":["openverse_audio","wikimedia_commons_audio"],
        "exhaustive":False,
        "rights_boundary":"intersection of caller policy with each member adapter provenance boundary"
    }
}

def adapter_registry():
    return {k:dict(v) for k,v in ADAPTERS.items()}

def projection_request(query,adapters,policy,budget):
    adapters=list(adapters or [])
    request={
        "protocol":PROTOCOL,
        "version":VERSION,
        "model":MODEL,
        "ontology_claim":"FORMAL_INFORMATION_MODEL_ONLY",
        "query":query,
        "adapters":adapters,
        "policy":policy or {},
        "budget":budget or {},
        "finite_projection":True,
        "global_exhaustion_claim":False,
        "search_space_identity":"IDEALIZED_NETWORK_INFORMATION_TOTALITY"
    }
    request["projection_uid"]=str(e257(canon(request).encode("utf-8")))
    return request

def projection_certificate(request,observations=None,status="UNRESOLVED"):
    observations=list(observations or [])
    cert={
        "protocol":PROTOCOL,
        "version":VERSION,
        "model":MODEL,
        "ontology_claim":"FORMAL_INFORMATION_MODEL_ONLY",
        "projection_uid":request["projection_uid"],
        "query":request["query"],
        "adapters":request["adapters"],
        "policy":request["policy"],
        "budget":request["budget"],
        "status":status,
        "finite_projection":True,
        "global_exhaustion_claim":False,
        "observations":observations,
        "epistemic_invariants":{
            "search_expands_evidence_only":True,
            "absence_of_retrieval_is_not_nonexistence":True,
            "source_failure_is_not_falsity":True,
            "budget_exhaustion_is_not_global_exhaustion":True,
            "adapter_scope_is_not_internet_totality":True
        },
        "blue":{
            "protocol":BLUE_PROTOCOL,
            "semantic_non_coercion":True,
            "semantic_humility":True,
            "provenance_required":True,
            "forced_totalization":False
        }
    }
    cert["certificate_uid"]=str(e257(canon(cert).encode("utf-8")))
    return cert

def main():
    import argparse
    ap=argparse.ArgumentParser(description="HSI NET Singularity — formal global-information-field projection model")
    ap.add_argument("query",nargs="*")
    ap.add_argument("--list-adapters",action="store_true")
    ap.add_argument("--adapter",action="append",default=[])
    ap.add_argument("--max-calls",type=int,default=12)
    ap.add_argument("--max-results",type=int,default=5)
    a=ap.parse_args()
    if a.list_adapters:
        print(canon({"protocol":PROTOCOL,"version":VERSION,"model":MODEL,"adapters":adapter_registry()}))
        return
    query=" ".join(a.query).strip()
    if not query:
        query=input("projection> ").strip()
    if not query:
        raise SystemExit("projection query required")
    adapters=a.adapter or ["network_audio"]
    unknown=[x for x in adapters if x not in ADAPTERS]
    status="UNRESOLVED" if unknown else "PROJECTABLE"
    req=projection_request(query,adapters,{},{"max_calls":a.max_calls,"max_results":a.max_results})
    obs=[{"adapter":x,"registry_state":ADAPTERS.get(x,{"status":"UNREGISTERED"})} for x in adapters]
    cert=projection_certificate(req,obs,status)
    print("protocol>",PROTOCOL)
    print("model>",MODEL)
    print("projection_uid>",req["projection_uid"])
    print("status>",status)
    print(canon(cert))

if __name__=="__main__":
    main()
