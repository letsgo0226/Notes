#!/usr/bin/env python3
import argparse, hashlib, json, os, socket, sys, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path
from hsi_net import projection_request, projection_certificate, VERSION as HSI_NET_VERSION

PROTOCOL="HSI-SEARCH/1.0"
VERSION="1.3.0"
BLUE_PROTOCOL="HSI-PLEIADIAN-BLUE-CARE/1.0"
DEFAULT_SOURCE="openverse_audio"

if hasattr(sys,"set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

def e257(data):
    n=1
    for b in data:
        n=n*257+b+1
    return n

def d257(n):
    out=bytearray()
    while n>1:
        n,r=divmod(n,257)
        if not 1<=r<=256:
            raise ValueError("invalid E257")
        out.append(r-1)
    out.reverse()
    return bytes(out)

def canon(x):
    return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":"))

def search_uid(query,source,policy,budget):
    request={"protocol":PROTOCOL,"query":query,"source":source,"policy":policy,"budget":budget}
    return str(e257(canon(request).encode("utf-8")))

def _query_plan(text):
    toks=[]
    seen=set()
    for raw in text.replace(","," ").split():
        t=raw.strip()
        if t and t.casefold() not in seen:
            seen.add(t.casefold());toks.append(t)
    if text not in toks:
        toks.append(text)
    return toks

def _http_json(url,timeout,retries,call_log,budget_state):
    headers={"User-Agent":"HSI-SEARCH/1.0","Accept":"application/json"}
    token=os.getenv("OPENVERSE_TOKEN","").strip()
    if token:
        headers["Authorization"]="Bearer "+token
    last=None
    for attempt in range(1,retries+1):
        if budget_state["calls"]>=budget_state["max_calls"]:
            budget_state["exhausted"]=True
            raise RuntimeError("HSI_SEARCH_BUDGET_EXHAUSTED")
        budget_state["calls"]+=1
        started=time.time()
        entry={"url":url,"attempt":attempt,"call_index":budget_state["calls"]}
        try:
            req=urllib.request.Request(url,headers=headers)
            with urllib.request.urlopen(req,timeout=timeout) as r:
                data=json.load(r)
            entry.update({"ok":True,"elapsed_ms":int((time.time()-started)*1000),"http_status":200})
            call_log.append(entry)
            return data
        except urllib.error.HTTPError as e:
            body=e.read().decode("utf-8","replace")
            entry.update({"ok":False,"elapsed_ms":int((time.time()-started)*1000),"http_status":e.code,"error":body[:300]})
            call_log.append(entry)
            if e.code not in (429,500,502,503,504):
                raise RuntimeError("HTTP %s"%e.code) from None
            last="HTTP %s"%e.code
        except (urllib.error.URLError,TimeoutError,socket.timeout) as e:
            last=str(getattr(e,"reason",e))
            entry.update({"ok":False,"elapsed_ms":int((time.time()-started)*1000),"error":last})
            call_log.append(entry)
        if attempt<retries:
            time.sleep(min(8,2**(attempt-1)))
    raise RuntimeError("SOURCE_UNAVAILABLE: %s"%last)

def _normalize_openverse(row,query,url):
    media=row.get("url")
    oid=str(row.get("id") or row.get("identifier") or hashlib.sha256(str(media).encode()).hexdigest()[:32])
    return {
        "record_uid":oid,
        "source":"openverse_audio",
        "title":row.get("title"),
        "creator":row.get("creator"),
        "creator_url":row.get("creator_url"),
        "license":str(row.get("license") or "").lower(),
        "license_version":row.get("license_version"),
        "filetype":str(row.get("filetype") or "").lower().lstrip("."),
        "media_url":media,
        "landing_url":row.get("foreign_landing_url"),
        "provider":row.get("provider"),
        "upstream_source":row.get("source"),
        "duration_ms":row.get("duration"),
        "filesize":row.get("filesize"),
        "sample_rate":row.get("sample_rate"),
        "category":str(row.get("category") or "").lower(),
        "genres":row.get("genres") or [],
        "tags":[(t.get("name") if isinstance(t,dict) else str(t)) for t in (row.get("tags") or [])],
        "alt_files":[
            {
                "url":a.get("url"),
                "filetype":str(a.get("filetype") or "").lower().lstrip("."),
                "filesize":a.get("filesize"),
                "bit_rate":a.get("bit_rate"),
                "sample_rate":a.get("sample_rate")
            }
            for a in (row.get("alt_files") or []) if isinstance(a,dict)
        ],
        "matched_query":query,
        "search_url":url,
        "assertion_basis":"OPENVERSE_INDEX_METADATA"
    }

def _select_media_variant(record,extensions):
    primary_type=str(record.get("filetype") or "").lower().lstrip(".")
    primary_url=record.get("media_url")
    if (not extensions or primary_type in extensions) and isinstance(primary_url,str) and primary_url.startswith(("http://","https://")):
        record["selected_media_variant"]="primary"
        return
    for alt in record.get("alt_files") or []:
        ft=str(alt.get("filetype") or "").lower().lstrip(".")
        u=alt.get("url")
        if (not extensions or ft in extensions) and isinstance(u,str) and u.startswith(("http://","https://")):
            record["primary_media_url"]=primary_url
            record["primary_filetype"]=primary_type
            record["media_url"]=u
            record["filetype"]=ft
            record["filesize"]=alt.get("filesize")
            record["sample_rate"]=alt.get("sample_rate")
            record["selected_media_variant"]="alt_file"
            return
    record["selected_media_variant"]="none"

def _admit(record,policy):
    reasons=[]
    licenses={str(x).lower() for x in policy.get("license_allow",[]) if str(x).strip()}
    extensions={str(x).lower().lstrip(".") for x in policy.get("extension_allow",[]) if str(x).strip()}
    categories={str(x).lower() for x in policy.get("category_allow",[]) if str(x).strip()}
    category_deny={str(x).lower() for x in policy.get("category_deny",[]) if str(x).strip()}
    _select_media_variant(record,extensions)
    if licenses and record.get("license") not in licenses:
        reasons.append("license_not_allowed")
    if extensions and record.get("filetype") not in extensions:
        reasons.append("extension_not_allowed")
    cat=record.get("category","")
    if categories and cat not in categories:
        reasons.append("category_not_allowed")
    if category_deny and cat in category_deny:
        reasons.append("category_denied")
    text=(" ".join([
        str(record.get("title") or ""),
        str(record.get("creator") or ""),
        str(record.get("creator_url") or ""),
        " ".join(str(x) for x in (record.get("tags") or []))
    ])).lower()
    if "lingualibre" in text or str(record.get("title") or "").startswith("LL-"):
        reasons.append("lexical_pronunciation_source")
    u=record.get("media_url")
    if not isinstance(u,str) or not u.startswith(("http://","https://")):
        reasons.append("missing_http_media_url")
    return not reasons,reasons

def run_search(query,source=DEFAULT_SOURCE,policy=None,budget=None,base_url=None):
    policy=dict(policy or {})
    budget=dict(budget or {})
    max_results=max(1,min(100,int(budget.get("max_results",5))))
    page_size=max(5,min(20,int(budget.get("page_size",10))))
    timeout=max(5,min(120,int(budget.get("timeout_seconds",24))))
    retries=max(1,min(5,int(budget.get("retries",3))))
    max_calls=max(1,min(100,int(budget.get("max_calls",12))))
    budget_norm={"max_results":max_results,"page_size":page_size,"timeout_seconds":timeout,"retries":retries,"max_calls":max_calls}
    uid=search_uid(query,source,policy,budget_norm)
    net_request=projection_request(query,[source],policy,budget_norm)
    call_log=[];accepted=[];rejected=[];seen=set();successful_responses=0
    budget_state={"calls":0,"max_calls":max_calls,"exhausted":False}
    if source!="openverse_audio":
        return {
            "protocol":PROTOCOL,"version":VERSION,"search_uid":uid,"query":query,"source":source,
            "policy":policy,"budget":budget_norm,"status":"UNRESOLVED","results":[],
            "rejected":[],"calls":[],"reason":"unsupported_source_adapter",
            "blue":{"protocol":BLUE_PROTOCOL,"semantic_non_coercion":True,"search_expands_evidence_only":True}
        }
    api=(base_url or os.getenv("HSI_OPENVERSE_BASE","https://api.openverse.org/v1/audio/")).rstrip("/")+"/"
    preferred=[str(x).strip() for x in policy.get("source_prefer",[]) if str(x).strip()]
    excluded=[str(x).strip() for x in policy.get("source_exclude",[]) if str(x).strip()]
    for q in _query_plan(query):
        stages=[]
        for src in preferred:
            stages.append({"filtered":True,"source":src})
        stages.append({"filtered":True,"source":None})
        stages.append({"filtered":False,"source":None})
        for stage in stages:
            if len(accepted)>=max_results or budget_state["exhausted"]:
                break
            params={"q":q,"page_size":page_size}
            if stage["source"]:
                params["source"]=stage["source"]
            if excluded:
                params["excluded_source"]=",".join(excluded)
            if stage["filtered"]:
                if policy.get("license_allow"):
                    params["license"]=",".join(policy["license_allow"])
                # Do not server-filter by extension here: an Openverse item may
                # expose an admissible WAV through alt_files while its primary
                # file is MP3/other.
                if policy.get("category_allow"):
                    params["category"]=",".join(policy["category_allow"])
            url=api+"?"+urllib.parse.urlencode(params)
            try:
                data=_http_json(url,timeout,retries,call_log,budget_state)
                successful_responses+=1
            except RuntimeError as e:
                if str(e)=="HSI_SEARCH_BUDGET_EXHAUSTED":
                    budget_state["exhausted"]=True
                    break
                continue
            rows=data.get("results") or []
            admitted_here=0
            for row in rows:
                rec=_normalize_openverse(row,q,url)
                rid=rec["record_uid"]
                if rid in seen:
                    continue
                seen.add(rid)
                ok,reasons=_admit(rec,policy)
                rec["admission_state"]="ADMITTED" if ok else "REJECTED"
                rec["verification_state"]="INDEX_ASSERTED"
                rec["rejection_reasons"]=reasons
                if ok:
                    accepted.append(rec);admitted_here+=1
                    if len(accepted)>=max_results:
                        break
                else:
                    rejected.append(rec)
            if admitted_here:
                break
    if accepted:
        status="FOUND"
    elif budget_state["exhausted"]:
        status="EXHAUSTED_BUDGET"
    elif successful_responses==0:
        status="SOURCE_UNAVAILABLE"
    else:
        status="UNRESOLVED"
    result={
        "protocol":PROTOCOL,"version":VERSION,"search_uid":uid,"query":query,"source":source,
        "policy":policy,"budget":budget_norm,"status":status,"results":accepted,
        "rejected":rejected,"calls":call_log,
        "budget_used":{"calls":budget_state["calls"],"exhausted":budget_state["exhausted"]},
        "net_protocol":"HSI-NET-SINGULARITY/1.0",
        "net_version":HSI_NET_VERSION,
        "net_projection":projection_certificate(
            net_request,
            [{
                "adapter":source,
                "successful_responses":successful_responses,
                "calls":budget_state["calls"],
                "accepted":len(accepted),
                "rejected":len(rejected),
                "budget_exhausted":budget_state["exhausted"]
            }],
            status
        ),
        "epistemic_rule":"absence_of_retrieval_is_not_evidence_of_nonexistence",
        "blue":{
            "protocol":BLUE_PROTOCOL,
            "semantic_non_coercion":True,
            "search_expands_evidence_only":True,
            "unresolved_is_valid":True,
            "forced_totalization":False
        }
    }
    result["search_certificate_uid"]=str(e257(canon(result).encode("utf-8")))
    return result

def main():
    ap=argparse.ArgumentParser(description="HSI SEARCH — finite evidence-expansion operator")
    ap.add_argument("query",nargs="*")
    ap.add_argument("--source",default=os.getenv("HSI_SEARCH_SOURCE",DEFAULT_SOURCE))
    ap.add_argument("--out",default=os.getenv("HSI_SEARCH_OUT"))
    ap.add_argument("--max-results",type=int,default=int(os.getenv("HSI_SEARCH_MAX_RESULTS","5")))
    ap.add_argument("--max-calls",type=int,default=int(os.getenv("HSI_SEARCH_MAX_CALLS","12")))
    ap.add_argument("--page-size",type=int,default=int(os.getenv("HSI_SEARCH_PAGE_SIZE","10")))
    ap.add_argument("--timeout",type=int,default=int(os.getenv("HSI_SEARCH_TIMEOUT","24")))
    ap.add_argument("--retries",type=int,default=int(os.getenv("HSI_SEARCH_RETRIES","3")))
    ap.add_argument("--license",default=os.getenv("HSI_SEARCH_LICENSE",""))
    ap.add_argument("--extension",default=os.getenv("HSI_SEARCH_EXTENSION",""))
    ap.add_argument("--category",default=os.getenv("HSI_SEARCH_CATEGORY",""))
    ap.add_argument("--prefer-source",action="append",default=[])
    ap.add_argument("--exclude-source",action="append",default=[])
    a=ap.parse_args()
    query=" ".join(a.query).strip()
    if not query:
        query=input("search> ").strip()
    if not query:
        raise SystemExit("search query required")
    policy={
        "license_allow":[x.strip().lower() for x in a.license.split(",") if x.strip()],
        "extension_allow":[x.strip().lower().lstrip(".") for x in a.extension.split(",") if x.strip()],
        "category_allow":[x.strip().lower() for x in a.category.split(",") if x.strip()],
        "source_prefer":[x.strip() for x in a.prefer_source if x.strip()],
        "source_exclude":[x.strip() for x in a.exclude_source if x.strip()]
    }
    budget={"max_results":a.max_results,"max_calls":a.max_calls,"page_size":a.page_size,"timeout_seconds":a.timeout,"retries":a.retries}
    r=run_search(query,a.source,policy,budget)
    if a.out:
        p=Path(a.out).expanduser();p.parent.mkdir(parents=True,exist_ok=True);p.write_text(canon(r)+"\n",encoding="utf-8")
    print("protocol>",PROTOCOL)
    print("search_uid>",r["search_uid"])
    print("source>",a.source)
    print("status>",r["status"])
    print("results>",len(r["results"]))
    print("calls>",r["budget_used"]["calls"])
    print(canon(r))
    raise SystemExit(0 if r["status"]=="FOUND" else 3)

if __name__=="__main__":
    main()
