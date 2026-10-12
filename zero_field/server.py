"""Read-only zero solver service; no externally chosen zeros and no state."""
import json,os
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit,parse_qs
from zero_field.model import evaluate,solve,decode_machine,PROTOCOL

class Handler(BaseHTTPRequestHandler):
    server_version="CosmicZeroField/2.0"
    def respond(self,status,body):
        raw=json.dumps(body,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Cache-Control","no-store")
        self.send_header("Content-Length",str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)
    def do_GET(self):
        try:
            if len(self.path)>1024:raise ValueError("request too long")
            target=urlsplit(self.path)
            if target.path=="/health" and not target.query:
                decode_machine()
                self.respond(200,{"status":"OK","protocol":PROTOCOL,
                                  "predefined_zeros":False,"read_only":True,
                                  "physical_energy_generated":False})
                return
            if target.path not in ("/","/evaluate","/solve"):
                self.respond(404,{"status":"NOT_FOUND"});return
            qs=parse_qs(target.query,keep_blank_values=True,max_num_fields=8)
            allowed={"n","sigma","t","amplitude"} if target.path in ("/","/evaluate") else {"n","tmax","max_roots"}
            if set(qs)-allowed or any(len(v)!=1 for v in qs.values()):
                raise ValueError("invalid or repeated parameter")
            if target.path=="/solve":
                result=solve(n=int(qs.get("n",["2"])[0]),
                             tmax=qs.get("tmax",["30"])[0],
                             max_roots=int(qs.get("max_roots",["12"])[0]))
            else:
                result=evaluate(n=int(qs.get("n",["16"])[0]),
                                sigma=qs.get("sigma",["0.5"])[0],
                                t=qs.get("t",["0"])[0],
                                amplitude=qs.get("amplitude",["1"])[0])
            self.respond(200,result)
        except (ValueError,TypeError,OverflowError) as err:
            self.respond(400,{"status":"INVALID_INPUT","error":str(err)[:160]})
    def do_POST(self):self.respond(405,{"status":"READ_ONLY"})
    def do_PUT(self):self.respond(405,{"status":"READ_ONLY"})
    def do_DELETE(self):self.respond(405,{"status":"READ_ONLY"})
    def log_message(self,*args):pass

def main():
    port=int(os.environ.get("PORT","8080"))
    if not 1024<=port<=65535:raise ValueError("invalid port")
    decode_machine()
    print("ZERO_FIELD_SELF_SOLVED_READY",flush=True)
    ThreadingHTTPServer(("0.0.0.0",port),Handler).serve_forever()

if __name__=="__main__":main()
