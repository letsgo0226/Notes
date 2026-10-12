#!/usr/bin/env python3
"""Finite HSI-CL-XY deployment witness + independent Open-Corpus audio gate.

This checks a deliberately restricted microkernel witness. It does NOT prove
semantic equivalence of arbitrary Python changes or aesthetic music quality.
"""
import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import wave
from array import array
from pathlib import Path

PROTOCOL = "HSI-CORPUS-DEPLOY-CLXY/1.0"
ROOT = Path(__file__).resolve().parent
MICROKERNEL = ROOT / "hsi_xy_analytic_2k" / "hsi_cl_xy_2k.sh"
PRIMES = {"rms": 2, "peak": 3, "crest": 5, "silence_ratio": 7, "stereo_balance": 11, "clip_ratio": 13}
BASELINE = {
    "rms": (0.025, 0.30),
    "peak": (0.15, 0.90),
    "crest": (1.1, 12.0),
    "silence_ratio": (0.0, 0.85),
    "stereo_balance": (0.0, 0.55),
    "clip_ratio": (0.0, 0.0),
}

def require(ok, message):
    if not ok:
        raise ValueError(message)

def canon(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def decode_257(num):
    n = int(num)
    require(n >= 1, "invalid E257 header")
    raw = bytearray()
    while n > 1:
        n, rem = divmod(n, 257)
        require(1 <= rem <= 256, "invalid E257 digit")
        raw.append(rem - 1)
    raw.reverse()
    return json.loads(bytes(raw).decode("utf-8"))

def microkernel_witness():
    require(MICROKERNEL.is_file(), "missing CL-XY microkernel")
    with tempfile.TemporaryDirectory(prefix="hsi-clxy-") as td:
        state = Path(td) / "state.json"
        env = dict(os.environ)
        env.update(HSI_STATE=str(state), HSI_PROGRAM="2", HSI_WORD="1")
        def check(**changes):
            e = dict(env)
            for key in ("HSI_RULE", "HSI_CAND", "HSI_PERM"):
                e.pop(key, None)
            e.update(changes)
            p = subprocess.run(["sh", str(MICROKERNEL)], env=e, cwd=td,
                               capture_output=True, text=True, timeout=15)
            require(p.returncode == 0, "CL-XY execution failed: " + p.stderr[-500:])
            o = json.loads(p.stdout)
            require(o.get("protocol") == "HSI-CL-XY/2K", "microkernel protocol mismatch")
            require(type(o.get("D0")) is int and type(o.get("D1_num")) is int,
                    "missing exact residual")
            y = decode_257(o["y"])
            d = load(state)
            require(y == [d["p"], d["q"], d["h"], d["m"]], "Gödel output not persisted configuration")
            event = decode_257(d["H"][-1])
            rr = event[-1]
            require(isinstance(rr, list) and len(rr) == 3 and all(type(x) is int and x >= 0 for x in rr),
                    "invalid residual vector")
            require(o["D0"] == sum(rr) and o["D1_num"] == 15*rr[0]+10*rr[1]+6*rr[2],
                    "incorrect Dirichlet certificate")
            require((o["D0"] == 0) == (o["D1_num"] == 0), "zero residual inconsistency")
            return o, d
        good, d1 = check()
        require(good["kind"] == "STEP" and good["accepted"] == 1
                and good["D0"] == 0 and good["D1_num"] == 0, "valid STEP not accepted")
        before = [d1[x] for x in ("p", "q", "h", "m", "n")]
        bad, d2 = check(HSI_CAND="[999,0,[]]")
        require(bad["accepted"] == 0 and bad["D0"] > 0 and bad["D1_num"] > 0,
                "incorrect STEP was accepted")
        require([d2[x] for x in ("p", "q", "h", "m", "n")] == before,
                "rejected STEP changed computation")
    with tempfile.TemporaryDirectory(prefix="hsi-clxy-evolve-") as td:
        state = Path(td) / "state.json"
        env = dict(os.environ)
        env.update(HSI_STATE=str(state), HSI_PROGRAM="2", HSI_WORD="1")
        def evolve(**changes):
            e = dict(env)
            for key in ("HSI_RULE", "HSI_PERM", "HSI_CAND"):
                e.pop(key, None)
            e.update(changes)
            p = subprocess.run(["sh", str(MICROKERNEL)], env=e, cwd=td,
                               capture_output=True, text=True, timeout=15)
            require(p.returncode == 0, "CL-XY EVOLVE execution failed: " + p.stderr[-500:])
            o = json.loads(p.stdout)
            d = load(state)
            rr = decode_257(d["H"][-1])[-1]
            require(o["D0"] == sum(rr) and o["D1_num"] == 15*rr[0]+10*rr[1]+6*rr[2],
                    "EVOLVE residual mismatch")
            require(decode_257(o["y"]) == [d["p"],d["q"],d["h"],d["m"]],
                    "EVOLVE Gödel mismatch")
            return o, d
        good_e, d1 = evolve(HSI_RULE="2", HSI_PERM="[0]")
        require(good_e["kind"] == "EVOLVE" and good_e["accepted"] == 1
                and good_e["D0"] == 0 and good_e["D1_num"] == 0, "identity EVOLVE failed")
        before = [d1[x] for x in ("p", "q", "h", "m", "n")]
        bad_e, d2 = evolve(HSI_RULE="2", HSI_PERM="[]")
        require(bad_e["accepted"] == 0 and bad_e["D1_num"] > 0
                and [d2[x] for x in ("p","q","h","m","n")] == before,
                "invalid EVOLVE was not rejected")
    return {
        "step_accepted": True, "bad_step_rejected": True,
        "evolve_accepted": True, "bad_evolve_rejected": True,
        "step_x": good["x"], "step_y": good["y"],
        "step_D0": good["D0"], "step_D1_num": good["D1_num"],
        "evolve_D0": good_e["D0"], "evolve_D1_num": good_e["D1_num"],
    }

def measure_wav(path):
    with wave.open(str(path), "rb") as w:
        require(w.getnchannels() == 2 and w.getsampwidth() == 2 and w.getcomptype() == "NONE",
                "audio shape not stereo PCM16")
        frames = w.getnframes()
        require(frames > 0, "empty WAV")
        raw = w.readframes(frames)
    pcm = array("h")
    pcm.frombytes(raw)
    if sys.byteorder != "little":
        pcm.byteswap()
    require(len(pcm) == frames*2, "WAV data length mismatch")
    a = b = 0.0
    peak = 0.0
    silence = clipped = 0
    for i in range(0, len(pcm), 2):
        li, ri = pcm[i], pcm[i+1]
        l, r = li/32768.0, ri/32768.0
        a += l*l
        b += r*r
        peak = max(peak, abs(l), abs(r))
        silence += int(abs(l) < .01 and abs(r) < .01)
        clipped += int(abs(li) >= 32760 or abs(ri) >= 32760)
    ll = math.sqrt(a/frames)
    rr = math.sqrt(b/frames)
    rms = math.sqrt((a+b)/(2*frames))
    return {"rms": rms, "peak": peak, "crest": peak/max(rms,1e-12),
            "silence_ratio": silence/frames,
            "stereo_balance": abs(ll-rr)/max(ll,rr,1e-12),
            "clip_ratio": clipped/frames}

def artifact_witness(out,expected_policy=None):
    cert = load(out/"song.hsicert")
    rc = load(out/"correspondence.hsicert")
    manifest = load(out/"manifest.json")
    require(cert["version"] in {"1.9.0", "1.9.1", "1.9.2", "1.9.3"}, "unexpected Open-Corpus version")
    require(cert["closed"] == 1 and cert["technical_closed"] == 1
            and cert["correspondence_closed"] == 1 and manifest["closed"] == 1,
            "audio not technically and correspondentially closed")
    require(cert["correspondence"] == rc, "song and correspondence certificates disagree")
    policy=cert["render_policy"]
    require(set(policy)=={"event_boost","fade_ms","gain_scale"},"unexpected policy field")
    require(type(policy["event_boost"]) is int and 0<=policy["event_boost"]<=4,
            "invalid event_boost")
    require(type(policy["fade_ms"]) is int and 100<=policy["fade_ms"]<=320,
            "invalid fade_ms")
    require(type(policy["gain_scale"]) in (int,float) and
            math.isfinite(policy["gain_scale"]) and .7<=policy["gain_scale"]<=1.3,
            "invalid gain_scale")
    uid=hashlib.sha256(canon(policy).encode("utf-8")).hexdigest()
    require(cert["render_policy_uid"]==uid and rc["render_policy_uid"]==uid
            and manifest["render_policy_uid"]==uid,"policy hash not reflected in all certificates")
    require(rc["render_policy"]==policy,"RC/render policies disagree")
    if expected_policy:
        expected=load(expected_policy)
        require(expected["protocol"]=="HSI-CORPUS-RENDER-POLICY/1.0"
                and {k:expected[k] for k in policy}==policy,
                "accepted proposal is not the rendered and verified policy")
    require(rc["protocol"] == "HSI-RC/1.0" and rc["sigma"] == "1/2",
            "unexpected correspondence protocol")
    require(rc["residual"] == 0 and rc["closed"] == 1, "nonzero correspondence residual")
    require(isinstance(cert["sources"],list) and len(cert["sources"]) >= 1,
            "missing provenance")
    require(all(str(x["license"]).lower() in ("cc0","pdm")
                and str(x["category"]).lower() in ("music","sound_effect")
                for x in cert["sources"]), "source metadata admission failed")
    wav = out/"song.wav"
    data = wav.read_bytes()
    require(hashlib.sha256(data).hexdigest() == cert["audio_sha256"],
            "WAV SHA-256 does not match song certificate")
    features = measure_wav(wav)
    require(rc["profile"] == {k:list(v) for k,v in BASELINE.items()},
            "correspondence profile differs from independently reviewed baseline")
    terms = rc["terms"]
    recomputed = 0.0
    for name, prime in PRIMES.items():
        x = features[name]
        require(math.isfinite(x) and math.isclose(x,rc["features"][name],rel_tol=1e-12,abs_tol=1e-12),
                "measured feature mismatch: " + name)
        lo,hi = BASELINE[name]
        delta = lo-x if x<lo else x-hi if x>hi else 0.0
        recomputed += delta*delta/prime
        require(terms[name]["prime"] == prime
                and math.isclose(terms[name]["distance"],delta,rel_tol=1e-12,abs_tol=1e-12),
                "term mismatch: " + name)
    require(recomputed == 0, "recomputed WAV correspondence failed")
    require(cert.get("rights_closed") in (0,1), "invalid rights assurance")
    return {"wav_sha256": cert["audio_sha256"], "candidate_index": cert["candidate_index"],
            "render_policy_uid":uid,
            "correspondence_residual": recomputed, "technical_closed": 1,
            "correspondence_closed": 1,
            "rights_independently_attested": bool(cert["rights_closed"])}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--artifact",required=True)
    parser.add_argument("--expected-policy")
    args=parser.parse_args()
    out=Path(args.artifact)
    try:
        clxy=microkernel_witness()
        artifact=artifact_witness(out,args.expected_policy)
        result={"protocol":PROTOCOL,"status":"VERIFIED","closed":1,
                "scope":"finite CL-XY witness + actual WAV correspondence and provenance metadata",
                "clxy":clxy,"artifact":artifact,
                "boundaries":{"arbitrary_python_equivalence_proved":False,
                              "aesthetic_quality_proved":False,
                              "publication_rights_automatically_cleared":False,
                              "Riemann_hypothesis_proved":False}}
        dest=out/"deployment.clxycert"
        tmp=out/"deployment.clxycert.tmp"
        tmp.write_text(canon(result)+"\n",encoding="utf-8")
        os.replace(tmp,dest)
        print(canon(result))
    except (OSError, ValueError, KeyError, IndexError, TypeError,
            subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        print(canon({"protocol":PROTOCOL,"status":"HOLD","closed":0,
                     "reason":str(exc)}),file=sys.stderr)
        raise SystemExit(3)

if __name__=="__main__":
    main()
