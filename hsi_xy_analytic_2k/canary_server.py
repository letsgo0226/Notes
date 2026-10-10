#!/usr/bin/env python3
"""Read-only, isolated HSI-CL-XY/2K deployment canary."""
import json,os,subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
HERE=Path(__file__).resolve().parent
SCRIPT=HERE/"hsi_cl_xy_2k.sh"
def prove():
 c=(HERE/"command.txt").read_bytes();s=SCRIPT.read_bytes()
 if not(c.startswith(b"python3 -c '") and len(c)==1799 and len(s)==1810):raise RuntimeError("interpreter identity/length mismatch")
 with TemporaryDirectory(prefix="hsi-cl-xy-canary-") as tmp:
  def test(name,cand=None):
   state=str(Path(tmp)/(name+".state"))
   env={"PATH":os.environ.get("PATH","/usr/bin:/bin"),"LANG":"C.UTF-8","HSI_STATE":state,"HSI_PROGRAM":"2","HSI_WORD":"1"}
   if cand is not None:env["HSI_CAND"]=cand
   r=subprocess.run(["sh",str(SCRIPT)],cwd=tmp,env=env,text=True,capture_output=True,timeout=15,check=True)
   out=json.loads(r.stdout);d=json.loads(Path(state).read_text())
   if out["protocol"]!="HSI-CL-XY/2K" or len(d["H"])!=1 or not(out["x"].isdigit() and out["y"].isdigit()):
    raise RuntimeError("invalid protocol, history, or XY coordinates")
   return out,d
  good,gd=test("good");bad,bd=test("bad","[99,0,[]]")
  if (good["accepted"],good["D0"],gd["n"])!=(1,0,1):raise RuntimeError("valid step not accepted")
  if bad["accepted"]!=0 or bad["D0"]<=0 or bd["n"]!=0:raise RuntimeError("invalid candidate passed")
 return {"status":"ok","protocol":"HSI-CL-XY/2K","command_bytes":len(c),"launcher_bytes":len(s),"accepted_step":gd["n"],"rejected_step":bd["n"],"rejected_residual":bad["D0"],"godel_history_verified":True,"trading_enabled":False,"live_actions":False,"proof_scope":"finite_transition_canary_only"}
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  if self.path not in ("/health","/evidence"):
   self.send_error(404);return
  body=json.dumps(EVIDENCE,separators=(",",":")).encode()
  self.send_response(200);self.send_header("Content-Type","application/json");self.send_header("Cache-Control","no-store");self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
 def log_message(self,*args):pass
if __name__=="__main__":
 EVIDENCE=prove()
 print(json.dumps(EVIDENCE),flush=True)
 ThreadingHTTPServer(("0.0.0.0",int(os.environ.get("PORT","8000"))),Handler).serve_forever()
