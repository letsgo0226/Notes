"""Bounded, reproducible resource observations for finite HSI triple-kernel runs.

Times and RSS are measurements of this *process on this host*, not hardware
invariants, universal complexity bounds, or evidence of mental phenomena.
"""
import argparse
import hashlib
import json
import os
import platform
import resource
import sys
import time
from pathlib import Path

from pleiadian_blue.cross_kernel import compare


def canonical(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()

def sample(p=1829,bits="1",steps=8):
    if type(p) is not int or p<0 or p>100000:
        raise ValueError("p out of bounds")
    if type(steps) is not int or steps<0 or steps>256:
        raise ValueError("steps out of bounds")
    if type(bits) is not str or len(bits)>128 or any(b not in "01" for b in bits):
        raise ValueError("bits must be <=128 binary characters")
    start_wall=time.perf_counter_ns()
    start_cpu=time.process_time_ns()
    result=compare(p,bits,steps)
    cpu_ns=time.process_time_ns()-start_cpu
    wall_ns=time.perf_counter_ns()-start_wall
    # ru_maxrss is kilobytes on Linux, bytes on macOS; peak since process start.
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    rss_bytes=int(rss*(1 if sys.platform=="darwin" else 1024))
    return {"protocol":"HSI-RESOURCE-CORRESPONDENCE/1",
            "input":{"p":p,"bits":bits,"steps":steps},
            "semantic_result":result,
            "semantic_sha256":hashlib.sha256(canonical(result)).hexdigest(),
            "environment":{"system":platform.system(),"machine":platform.machine(),
                           "python":platform.python_version(),
                           "rss_is_process_peak":True},
            "measurement":{"wall_ns":wall_ns,"process_cpu_ns":cpu_ns,
                           "peak_process_rss_bytes":rss_bytes},
            "limits":["finite_reference_simulation","peak_rss_not_incremental",
                      "time_is_host_dependent","no_hardware_limit_bypass"]}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--p",type=int,default=1829)
    parser.add_argument("--bits",default="1")
    parser.add_argument("--steps",type=int,default=8)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    result=sample(args.p,args.bits,args.steps)
    encoded=canonical(result)+b"\n"
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        temporary=args.output.with_name(args.output.name+".tmp")
        with temporary.open("wb") as f:
            f.write(encoded);f.flush();os.fsync(f.fileno())
        os.replace(temporary,args.output)
    print(encoded.decode().rstrip())

if __name__=="__main__":
    main()
