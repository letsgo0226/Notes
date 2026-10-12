#!/usr/bin/env python3
"""Independent read-only candidate verification; NEVER deploy or trade."""
import argparse,json,os,re,sys
from math import isqrt
from urllib.request import Request,urlopen
from urllib.parse import urlencode
REPO="letsgo0226/Notes";PR=29
BRANCH="cosmic-love-closure-review-20261013"
WORKFLOW="Cosmic Love — finite TM closure smoke"
SHA=re.compile(r"[0-9a-f]{40}\Z")
PROJECT="bf5f3c0b-f22e-47a4-a1d2-82e7e215f591"
ENV="d00f20c7-153c-4b42-aa59-eeed8ec2d354"
PRIMARY="ae9b70a1-23c4-4041-bf1e-c128863f8758"
class Hold(ValueError):pass
def theorem():
 old=[]
 for k in range(2,33,2):
  K=k+1;B=4*K
  c=sum(((2*a+1-q%2)*K+(q^1))*B**(2*q+a) for q in range(k) for a in (0,1))
  v=c+k-1;p=v*(v+1)//2+c
  w=(isqrt(8*p+1)-1)//2;d=p-w*(w+1)//2
  if w-d+1!=k or k==2 and p!=55067263:raise Hold("HOLD_BAD_TM_ENCODING")
  rows=[]
  for q in range(k):
   for a in (0,1):
    u=d//B**(2*q+a)%B;z,r=divmod(u,K)
    rows.append((q,a,r,z//2,2*(z%2)-1))
  if rows[:len(old)]!=old:raise Hold("HOLD_NOT_CONSERVATIVE")
  for q,a,r,b,m in rows:
   if (r,b,m)!=(q^1,a,1-2*(q%2)) or rows[2*r+b][2:]!=(q,a,-m):
    raise Hold("HOLD_BAD_TWO_STEP_CYCLE")
  old=rows
 return "FINITE_REFERENCE_CLOSED_LOOP_VERIFIED"
def fetch(url):
 h={"User-Agent":"cosmic-love-independent-controller","Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28"}
 if os.getenv("GITHUB_TOKEN"):h["Authorization"]="Bearer "+os.environ["GITHUB_TOKEN"]
 with urlopen(Request(url,headers=h),timeout=15) as r:
  raw=r.read(524289)
 if len(raw)>524288:raise Hold("HOLD_RESPONSE_TOO_LARGE")
 return json.loads(raw)
def check(candidate,get=fetch):
 if type(candidate) is not str or not SHA.fullmatch(candidate):raise Hold("HOLD_INVALID_SHA")
 base="https://api.github.com/repos/"+REPO
 pr=get(base+"/pulls/29")
 if (pr.get("number")!=29 or pr.get("state")!="open" or pr.get("draft") is not True or
     pr.get("merged") is not False or pr.get("base",{}).get("ref")!="main" or
     pr.get("head",{}).get("ref")!=BRANCH or pr.get("head",{}).get("sha")!=candidate or
     pr.get("head",{}).get("repo",{}).get("full_name")!=REPO):
  raise Hold("HOLD_PR_IDENTITY_OR_SHA")
 runs=get(base+"/actions/runs?"+urlencode({"head_sha":candidate,"per_page":100}))
 ok=[r for r in runs.get("workflow_runs",[]) if r.get("head_sha")==candidate and
     r.get("name")==WORKFLOW and r.get("event")=="pull_request" and
     r.get("status")=="completed" and r.get("conclusion")=="success"]
 if not ok:raise Hold("HOLD_NO_SUCCESSFUL_PINNED_CI")
 files=[]
 for page in range(1,7):
  batch=get(base+"/pulls/29/files?"+urlencode({"per_page":100,"page":page}))
  if type(batch) is not list or len(files)+len(batch)>500:raise Hold("HOLD_FILE_LIST_LIMIT")
  files+=batch
  if len(batch)<100:break
 if not files or any(type(f) is not dict or
     not (f.get("filename","").startswith("cosmic_love/") or
          f.get("filename")==".github/workflows/cosmic_love_smoke.yml") for f in files):
  raise Hold("HOLD_UNEXPECTED_PATH")
 return {"status":"CANARY_ELIGIBLE_NOT_DEPLOYED","sha":candidate,
         "source_run_id":max(r["id"] for r in ok),"paths":len(files),
         "proof":theorem(),"project":PROJECT,"environment":ENV,
         "primary_service":PRIMARY,"canary_only":True,
         "primary_replacement":False,"live_trading":False,"auto_merge":False}
def promote(candidate_receipt,verified_backup=False,rollback_test=False):
 if candidate_receipt.get("status")!="CANARY_ELIGIBLE_NOT_DEPLOYED":
  raise Hold("HOLD_UNVERIFIED_CANARY")
 if not (verified_backup and rollback_test):raise Hold("HOLD_BACKUP_AND_ROLLBACK_REQUIRED")
 # Untrusted booleans are not off-site attestations: promotion is impossible here.
 raise Hold("HOLD_EXTERNAL_RECOVERY_NOT_ATTESTED")
def main():
 p=argparse.ArgumentParser();p.add_argument("--candidate-sha",required=True)
 a=p.parse_args()
 try:print(json.dumps(check(a.candidate_sha),sort_keys=True,indent=2));return 0
 except (Hold,OSError,ValueError,TimeoutError) as e:
  print(json.dumps({"status":"HOLD","reason":str(e)},sort_keys=True));return 2
if __name__=="__main__":sys.exit(main())
