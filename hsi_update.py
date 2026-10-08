#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, sys, time
from pathlib import Path

PROTOCOL="HSI-UPDATE/1.0"
VERSION="1.0.0"
BLUE_PROTOCOL="HSI-PLEIADIAN-BLUE-CARE/1.0"

if hasattr(sys,"set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

def e257(data: bytes) -> int:
    n=1
    for b in data:
        n=n*257+b+1
    return n

def canon(x):
    return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":"))

def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def artifact_paths(root):
    root=Path(root).expanduser()
    return {
        "root":root,
        "manifest":root/"manifest.json",
        "song_cert":root/"song.hsicert",
        "lock":root/"corpus.lock.json",
        "events":root/"events.json",
        "search_cert":root/"search.hsicert",
    }

def require(paths):
    missing=[str(p) for k,p in paths.items() if k!="root" and not p.exists()]
    if missing:
        raise SystemExit("missing artifact files: "+", ".join(missing))

def analyze(root):
    p=artifact_paths(root)
    require(p)
    manifest=load_json(p["manifest"])
    cert=load_json(p["song_cert"])
    lock=load_json(p["lock"])
    events=load_json(p["events"])
    search=load_json(p["search_cert"])

    sources=cert.get("sources") or lock.get("sources") or []
    source_ids=[str(x.get("source_id") or x.get("openverse_id") or "") for x in sources]
    event_source_ids=[str(x.get("source_id") or "") for x in events]
    unique_event_sources=sorted({x for x in event_source_ids if x})
    event_counts={sid:event_source_ids.count(sid) for sid in unique_event_sources}
    max_share=(max(event_counts.values())/len(events)) if events and event_counts else 0.0

    findings=[]
    def add(code,severity,evidence,meaning):
        findings.append({"code":code,"severity":severity,"evidence":evidence,"meaning":meaning})

    technical_closed=int(manifest.get("closed",cert.get("technical_closed",0)) or 0)
    rights_closed=int(manifest.get("rights_closed",cert.get("rights_closed",0)) or 0)
    if not technical_closed:
        add("TECHNICAL_NOT_CLOSED","BLOCKING",
            {"manifest_closed":technical_closed},
            "The artifact is not a valid technical baseline for quality-oriented evolution.")
    if rights_closed==0:
        add("RIGHTS_REVIEW_OPEN","BOUNDARY",
            {"rights_closed":0},
            "Source rights are metadata-asserted but not independently attested; publication/commercial use remains outside automatic closure.")

    if len(unique_event_sources)<2 and len(events)>0:
        add("SINGLE_SOURCE_COLLAPSE","QUALITY",
            {"unique_event_sources":len(unique_event_sources),"events":len(events),"event_counts":event_counts},
            "The composition repeatedly transforms one source instead of forming a genuinely multi-source structure.")
    elif len(unique_event_sources)<3 and len(events)>=6:
        add("SOURCE_DIVERSITY_LOW","QUALITY",
            {"unique_event_sources":len(unique_event_sources),"events":len(events),"event_counts":event_counts},
            "Source diversity is low relative to event count.")

    if max_share>0.60 and len(events)>=5:
        add("SOURCE_DOMINANCE_HIGH","QUALITY",
            {"max_event_share":round(max_share,6),"event_counts":event_counts},
            "One source accounts for more than 60% of rendered events.")

    partial=[x for x in sources if x.get("partial_source")]
    if partial:
        add("FINITE_PREFIX_SAMPLING_USED","INFO",
            {"partial_sources":len(partial),
             "downloaded_bytes":sum(int(x.get("downloaded_bytes") or 0) for x in partial),
             "source_total_bytes":sum(int(x.get("source_total_bytes") or 0) for x in partial)},
            "Large WAV material was intentionally observed through a finite byte prefix; this is not itself a failure.")

    rejected=((search.get("renderer_admission") or {}).get("rejected") or []) + (search.get("rejected") or [])
    speech_rejections=sum(1 for x in rejected if any(
        r in {"category_denied","lexical_pronunciation_source","renderer_spoken_word_category","renderer_lexical_pronunciation_source"}
        for r in (x.get("rejection_reasons") or x.get("renderer_rejection_reasons") or [])
    ))
    if speech_rejections:
        add("SPEECH_GATE_OBSERVED","INFO",
            {"rejected_spoken_word_candidates":speech_rejections},
            "The spoken-word/pronunciation exclusion gate is active and should be preserved in future updates.")

    observation={
        "artifact_root":str(Path(root).expanduser()),
        "protocol":cert.get("protocol"),
        "open_corpus_version":cert.get("version"),
        "search_protocol":cert.get("search_protocol"),
        "search_status":cert.get("search_status") or search.get("status"),
        "technical_closed":technical_closed,
        "rights_closed":rights_closed,
        "source_count":len(sources),
        "unique_event_sources":len(unique_event_sources),
        "event_count":len(events),
        "max_event_source_share":round(max_share,6),
        "event_counts":event_counts,
        "partial_source_count":len(partial),
        "findings":findings
    }
    observation["observation_uid"]=str(e257(canon(observation).encode("utf-8")))
    return observation

def solve(observation):
    codes={x["code"] for x in observation["findings"]}
    candidates=[]

    if "TECHNICAL_NOT_CLOSED" in codes:
        candidates.append({
            "id":"RESTORE_TECHNICAL_CLOSURE",
            "priority":100,
            "kind":"repair",
            "goal":"Restore a technically closed baseline before quality evolution.",
            "changes":[
                "Preserve fail-closed source admission.",
                "Repair the specific technical invariant reported by the artifact.",
                "Re-run deterministic replay and E257 round-trip."
            ],
            "acceptance":[
                "technical_closed == 1",
                "manifest.closed == 1",
                "locked offline rerender is byte-identical"
            ]
        })
    else:
        if "SINGLE_SOURCE_COLLAPSE" in codes or "SOURCE_DIVERSITY_LOW" in codes or "SOURCE_DOMINANCE_HIGH" in codes:
            candidates.append({
                "id":"MULTI_SOURCE_COMPOSITION_V1",
                "priority":90,
                "kind":"quality",
                "goal":"Move from single-source collage toward deterministic multi-source composition without AI.",
                "changes":[
                    "Search beyond the first admitted result until the finite budget is exhausted or at least 3 usable sources are admitted.",
                    "Require at least 2 unique rendered sources when 2+ usable sources exist.",
                    "When 3+ usable sources exist, target at least 3 unique rendered sources.",
                    "Cap planned event share of one source at 60% when multiple usable sources exist.",
                    "Preserve CC0/PDM, WAV, music/sound_effect, and spoken-word exclusion gates.",
                    "Do not fabricate source diversity when the finite search projection finds only one usable source; return DEGRADED_SINGLE_SOURCE or use explicitly enabled Native connective synthesis."
                ],
                "acceptance":[
                    "speech/provenance/license gates unchanged",
                    "if usable_sources >= 2 then unique_event_sources >= 2",
                    "if usable_sources >= 3 then unique_event_sources >= 3",
                    "if unique_event_sources >= 2 then max_event_source_share <= 0.60",
                    "technical_closed == 1",
                    "offline locked rerender remains byte-identical"
                ]
            })
            candidates.append({
                "id":"OPTIONAL_NATIVE_CONNECTIVE_LAYER",
                "priority":70,
                "kind":"fallback",
                "goal":"Avoid total dependence on one retrieved recording when network evidence is sparse.",
                "changes":[
                    "Keep corpus audio as provenance-bearing material.",
                    "Permit deterministic Native synthesis only as a separately labelled connective layer.",
                    "Record native_event_count and corpus_event_count separately.",
                    "Never present Native-generated material as retrieved corpus material."
                ],
                "acceptance":[
                    "ai_model == false",
                    "retrieved and native provenance remain distinguishable",
                    "no relaxation of rights or speech gates"
                ]
            })

    if "RIGHTS_REVIEW_OPEN" in codes:
        candidates.append({
            "id":"RIGHTS_ATTESTATION_WORKFLOW",
            "priority":40,
            "kind":"boundary",
            "goal":"Keep technical generation separate from publication-rights closure.",
            "changes":[
                "Preserve rights_closed=0 by default.",
                "Allow rights_closed=1 only after explicit independent source-rights attestation.",
                "Never infer rights closure from search metadata alone."
            ],
            "acceptance":[
                "rights_closed remains 0 without explicit attestation",
                "technical_closed is independent of rights_closed"
            ]
        })

    candidates=sorted(candidates,key=lambda x:(-x["priority"],x["id"]))
    blocking=any(x["severity"]=="BLOCKING" for x in observation["findings"])
    status="HOLD" if blocking else ("UPDATE_CANDIDATE" if candidates else "NO_UPDATE_REQUIRED")
    plan={
        "protocol":PROTOCOL,
        "version":VERSION,
        "status":status,
        "observation_uid":observation["observation_uid"],
        "observation":observation,
        "candidate_updates":candidates,
        "policy":{
            "automatic_source_code_rewrite":False,
            "automatic_git_push":False,
            "human_approval_required_before_repository_mutation":True,
            "regression_tests_required_before_commit":True,
            "preserve_semantic_humility":True,
            "preserve_no_ai_claim_unless_explicitly_changed":True
        },
        "blue":{
            "protocol":BLUE_PROTOCOL,
            "semantic_non_coercion":True,
            "forced_totalization":False,
            "unresolved_is_valid":True
        }
    }
    plan["plan_uid"]=str(e257(canon(plan).encode("utf-8")))
    return plan

def main():
    ap=argparse.ArgumentParser(description="HSI UPDATE — artifact-driven finite update solver")
    ap.add_argument("artifact",help="Path to an HSI Open-Corpus output directory")
    ap.add_argument("--out",default=None,help="Optional output plan path")
    ap.add_argument("--json",action="store_true")
    a=ap.parse_args()

    obs=analyze(a.artifact)
    plan=solve(obs)
    out=Path(a.out).expanduser() if a.out else Path(a.artifact).expanduser()/"update.hsicert"
    out.write_text(canon(plan)+"\n",encoding="utf-8")

    print("protocol>",PROTOCOL)
    print("observation_uid>",obs["observation_uid"])
    print("status>",plan["status"])
    print("findings>",",".join(x["code"] for x in obs["findings"]) or "NONE")
    print("candidates>",",".join(x["id"] for x in plan["candidate_updates"]) or "NONE")
    print("plan>",out)
    if a.json:print(canon(plan))
    raise SystemExit(0 if plan["status"]!="HOLD" else 3)

if __name__=="__main__":
    main()
