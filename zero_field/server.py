"""Read-only HTTP service for zero-field numerical research."""
import json
import os
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit,parse_qs
from zero_field.model import evaluate,decode_machine,DEFAULT_ZERO,PROTOCOL

class Handler(BaseHTTPRequestHandler):
    server_version="CosmicZeroField/1.0"
    def respond(self,status,body):
        wire=json.dumps(body,ensure_ascii=False,sort_keys=True,allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Cache-Control","no-store")
        self.send_header("Content-Length",str(len(wire)))
        self.end_headers()
        self.wfile.write(wire)
    def do_GET(self):
        try:
            target=urlsplit(self.path)
            if len(self.path)>1024:raise ValueError("request too long")
            if target.path=="/health":
                if target.query:raise ValueError("unexpected health parameters")
                decode_machine()
                self.respond(200,{"status":"OK","protocol":PROTOCOL,"read_only":True,
                                  "seed_verified":True,"physical_energy_generated":False})
                return
            if target.path not in ("/evaluate","/"):
                self.respond(404,{"status":"NOT_FOUND"});return
            query=parse_qs(target.query,keep_blank_values=True,max_num_fields=12)
            if set(query)-{"sigma","t","n","amplitude","z"}:
                raise ValueError("unexpected query parameter")
            if any(len(v)!=1 for k,v in query.items() if k!="z"):
                raise ValueError("duplicate parameter")
            if len(query.get("z",[]))>4:raise ValueError("too many zeros")
            zeros=[]
            for item in query.get("z",[]):
                bits=item.split(",")
                if len(bits)!=2:raise ValueError("zero must be real,imag")
                zeros.append(complex(float(bits[0]),float(bits[1])))
            n=int(query.get("n",["16"])[0])
            result=evaluate(sigma=query.get("sigma",["0.5"])[0],
                            t=query.get("t",["0"])[0],n=n,
                            zeros=tuple(zeros) if zeros else (DEFAULT_ZERO,),
                            amplitude=query.get("amplitude",["1"])[0])
            self.respond(200,result)
        except (ValueError,OverflowError,TypeError) as e:
            self.respond(400,{"status":"INVALID_INPUT","error":str(e)[:200]})
    def do_POST(self):self.respond(405,{"status":"READ_ONLY"})
    def do_PUT(self):self.respond(405,{"status":"READ_ONLY"})
    def do_DELETE(self):self.respond(405,{"status":"READ_ONLY"})
    def log_message(self,*args):pass

def main():
    port=int(os.environ.get("PORT","8080"))
    if not 1024<=port<=65535:raise ValueError("invalid PORT")
    assert evaluate()["not_physical_energy"]
    print("ZERO_FIELD_MATH_READY protocol="+PROTOCOL,flush=True)
    ThreadingHTTPServer(("0.0.0.0",port),Handler).serve_forever()

if __name__=="__main__":main()
