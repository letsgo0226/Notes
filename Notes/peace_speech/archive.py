#!/usr/bin/env python3
"""Add verified generated media to the persistent 影音/ archive index.

The GitHub Actions workflow commits these records only on the default branch.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess

REPO=Path(__file__).resolve().parent.parent.parent
ARCHIVE=REPO/"影音"
REQUIRED=("peace_address_english.mp4","voiceover.en.mp3","captions.en.srt",
          "transcript.en.md","correspondence.json","frame_correspondence.jsonl","SHA256SUMS")

def digest(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--run-id",required=True)
    ap.add_argument("--max-file-mib",type=int,default=60)
    args=ap.parse_args()
    if not re.fullmatch(r"\d{4,20}",args.run_id):
        raise ValueError("invalid GitHub run ID")
    folder=ARCHIVE/"runs"/args.run_id
    folder=folder.resolve()
    if not str(folder).startswith(str(ARCHIVE.resolve())+"/"):
        raise ValueError("unsafe archive directory")
    import sys
    sys.path.insert(0,str(REPO/"Notes"/"peace_speech"))
    from render_long import duration
    entries=[]
    for name in REQUIRED:
        path=folder/name
        if not path.is_file():
            raise FileNotFoundError(path)
        if path.stat().st_size > args.max_file_mib * (1024**2):
            raise ValueError(f"Media too large for safe Git commit: {name}. Use GitHub Release assets instead.")
        entries.append({"file":name,"bytes":path.stat().st_size,"sha256":digest(path)})
    video=folder/"peace_address_english.mp4"
    runtime=duration(video)
    if runtime<600.0:
        raise ValueError("less than ten minutes")
    verify=subprocess.run(["sha256sum","-c","SHA256SUMS"],
        cwd=folder,capture_output=True,text=True)
    if verify.returncode:
        raise ValueError("sha256 verification failed: "+verify.stdout+verify.stderr)
    c=json.loads((folder/"correspondence.json").read_text(encoding="utf-8"))
    if not c.get("not_a_real_political_event") or c["picture"].get("natural_lip_sync") is not False:
        raise ValueError("false synthetic provenance or lip-sync declaration")
    manifest={
        "protocol":"HSI-PEACE-AV-ARCHIVE/1.0","run_id":args.run_id,
        "video_duration_seconds":round(runtime,3),
        "video_language":"English",
        "speaker_performance":"STATIC_VISUAL_FALLBACK__NO_LIP_SYNC",
        "real_world_peace_claim":"NOT_ASSESSED",
        "scene_count":len(c["scenes"]),"outputs":entries
    }
    (folder/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    ARCHIVE.mkdir(parents=True,exist_ok=True)
    ix=ARCHIVE/"index.json"
    current=json.loads(ix.read_text(encoding="utf-8")) if ix.exists() else {"protocol":"HSI-PEACE-AV-LIBRARY/1.0","runs":[]}
    current["runs"]=[r for r in current["runs"] if r["run_id"]!=args.run_id]+[
        {"run_id":args.run_id, "directory":f"影音/runs/{args.run_id}",
         "manifest":f"影音/runs/{args.run_id}/manifest.json",
         "film":f"影音/runs/{args.run_id}/peace_address_english.mp4",
         "duration_seconds":round(runtime,3),"lang":"en"}]
    current["runs"].sort(key=lambda x:int(x["run_id"]),reverse=True)
    ix.write_text(json.dumps(current,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"status":"ARCHIVE_VERIFIED","dir":str(folder.relative_to(REPO)),
                      "duration":round(runtime,3),"files":len(entries)},ensure_ascii=False))


if __name__=="__main__":
    main()
