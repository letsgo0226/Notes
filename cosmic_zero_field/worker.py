"""Read-only simulation heartbeat; finite work per cycle, no sensitive APIs."""
import argparse
import json
import time
from cosmic_zero_field.model import Config,Field

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--interval',type=float,default=300)
    p.add_argument('--once',action='store_true')
    args=p.parse_args(argv)
    if not (1<=args.interval<=86400):p.error('interval must be 1..86400 seconds')
    f=Field(Config())
    while True:
        result=f.report()
        print(json.dumps(result,sort_keys=True,separators=(',',':')),flush=True)
        if args.once:return 0
        time.sleep(args.interval)

if __name__=='__main__':raise SystemExit(main())
