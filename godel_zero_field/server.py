"""Read-only strictly-integer API for exact Gödel-coded mathematical results."""
import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit
from .core import PROTOCOL, machine_rules, model_certificate, evaluate_integer, symbolic_root_n2, receipt_digest

INTEGER = re.compile(r'(?:0|-?[1-9][0-9]*)\Z')

def integer(query,name,default):
    vals = query.get(name,[default])
    if len(vals)!=1 or len(vals[0])>12 or not INTEGER.fullmatch(vals[0]):
        raise ValueError('invalid exact integer: '+name)
    return int(vals[0])

class Handler(BaseHTTPRequestHandler):
    server_version='CosmicLoveGodel/1.0'

    def respond(self,status,payload):
        wire=json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Length',str(len(wire)))
        self.end_headers()
        self.wfile.write(wire)

    def do_GET(self):
        try:
            if len(self.path)>512:
                raise ValueError('request path too long')
            path=urlsplit(self.path)
            q=parse_qs(path.query,strict_parsing=True,max_num_fields=6)
            if path.path=='/health':
                if q:raise ValueError('unexpected health parameters')
                machine_rules()
                return self.respond(200,{'status':'OK','protocol':PROTOCOL,
                                         'read_only':True,'float_mode_enabled':False,
                                         'orders_submitted':False})
            if path.path=='/model':
                if set(q)-{'n'}:raise ValueError('unexpected parameter')
                result=model_certificate(integer(q,'n','16'))
            elif path.path=='/evaluate':
                if set(q)-{'n','s','a_num','a_den'}:raise ValueError('unexpected parameter')
                result=evaluate_integer(integer(q,'n','16'),integer(q,'s','0'),
                                        integer(q,'a_num','1'),integer(q,'a_den','1'))
            elif path.path=='/symbolic-root':
                if set(q)-{'k'}:raise ValueError('unexpected parameter')
                result=symbolic_root_n2(integer(q,'k','0'))
            else:
                return self.respond(404,{'status':'NOT_FOUND'})
            return self.respond(200,{'receipt':result,'receipt_sha256':receipt_digest(result)})
        except (ValueError, OverflowError, TypeError) as e:
            return self.respond(400,{'status':'INVALID_EXACT_INPUT','message':str(e)[:120]})

    def do_POST(self):return self.respond(405,{'status':'READ_ONLY'})
    def do_PUT(self):return self.respond(405,{'status':'READ_ONLY'})
    def do_DELETE(self):return self.respond(405,{'status':'READ_ONLY'})
    def log_message(self,*args):pass

def main():
    port=int(os.environ.get('PORT','8080'))
    if not 1024<=port<=65535:raise ValueError('invalid port')
    machine_rules()
    print('COSMIC_GODEL_ZERO_FIELD_READY',flush=True)
    ThreadingHTTPServer(('0.0.0.0',port),Handler).serve_forever()

if __name__=='__main__':main()
