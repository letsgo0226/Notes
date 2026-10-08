#!/usr/bin/env python3
import argparse, hashlib, json, math, os, random, struct, sys, time, urllib.request, wave
from array import array
from pathlib import Path
from hsi_search import run_search

PROTOCOL="HSI-OPEN-CORPUS/1.0"
BLUE_PROTOCOL="HSI-PLEIADIAN-BLUE-CARE/1.0"
VERSION="1.1.0"
API=os.getenv("HSI_OPENVERSE_BASE","https://api.openverse.org/v1/audio/").rstrip("/")+"/"
CACHE=Path(os.getenv("HSI_CORPUS_CACHE",str(Path.home()/".hsi-corpus"/"cache"))).expanduser()
MAX_ITEMS=max(2,min(8,int(os.getenv("HSI_CORPUS_ITEMS","5"))))
SEARCH_PAGE=max(5,min(20,int(os.getenv("HSI_OPENVERSE_PAGE_SIZE","10"))))
SEARCH_TIMEOUT=max(8,min(120,int(os.getenv("HSI_OPENVERSE_TIMEOUT","24"))))
SEARCH_RETRIES=max(1,min(5,int(os.getenv("HSI_OPENVERSE_RETRIES","3"))))
MAX_BYTES=max(1048576,min(50*1048576,int(os.getenv("HSI_CORPUS_MAX_BYTES",str(18*1048576)))))
TARGET_SR=max(16000,min(48000,int(os.getenv("HSI_CORPUS_SR","32000"))))
E257_ENABLED=os.getenv("HSI_E257","1")!="0"
LOCK_ENV=os.getenv("HSI_CORPUS_LOCK","").strip()
RIGHTS_ATTESTED=os.getenv("HSI_RIGHTS_VERIFIED","0")=="1"
ALLOWED_LICENSES={"cc0","pdm"}

if hasattr(sys,"set_int_max_str_digits"): sys.set_int_max_str_digits(0)

def e257(data):
    n=1
    for b in data:n=n*257+b+1
    return n

def d257(n):
    out=bytearray()
    while n>1:
        n,r=divmod(n,257)
        if not 1<=r<=256: raise ValueError("invalid E257")
        out.append(r-1)
    out.reverse();return bytes(out)

def canon(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":"))

class PRNG:
    def __init__(self,n):
        self.x=(n^(n>>64)^0x9E3779B97F4A7C15)&((1<<64)-1) or 1
    def u64(self):
        self.x=(self.x+0x9E3779B97F4A7C15)&((1<<64)-1)
        z=self.x;z=(z^(z>>30))*0xBF58476D1CE4E5B9&((1<<64)-1)
        z=(z^(z>>27))*0x94D049BB133111EB&((1<<64)-1)
        return (z^(z>>31))&((1<<64)-1)
    def unit(self):return self.u64()/float(1<<64)
    def pick(self,n):return self.u64()%n

def discover(text):
    policy={"license_allow":["cc0","pdm"],"extension_allow":["wav"]}
    budget={
        "max_results":MAX_ITEMS,
        "page_size":SEARCH_PAGE,
        "timeout_seconds":SEARCH_TIMEOUT,
        "retries":SEARCH_RETRIES,
        "max_calls":max(8,min(40,SEARCH_RETRIES*8))
    }
    cert=run_search(text,source="openverse_audio",policy=policy,budget=budget,base_url=API)
    items=[]
    for x in cert.get("results") or []:
        items.append({
            "openverse_id":x.get("record_uid"),
            "title":x.get("title"),
            "creator":x.get("creator"),
            "creator_url":x.get("creator_url"),
            "license":x.get("license"),
            "license_version":x.get("license_version"),
            "media_url":x.get("media_url"),
            "landing_url":x.get("landing_url"),
            "provider":x.get("provider"),
            "source":x.get("upstream_source"),
            "filetype":x.get("filetype"),
            "duration_ms":x.get("duration_ms"),
            "filesize":x.get("filesize"),
            "sample_rate":x.get("sample_rate"),
            "query":x.get("matched_query"),
            "openverse_search_url":x.get("search_url"),
            "license_basis":x.get("assertion_basis"),
            "license_independently_verified":False
        })
    return items,cert

def cache_path(item):
    safe="".join(c if c.isalnum() or c in "-_" else "_" for c in item["openverse_id"])
    return CACHE/(safe+".wav")

def download(item):
    CACHE.mkdir(parents=True,exist_ok=True)
    p=cache_path(item)
    if p.exists() and p.stat().st_size>44:
        raw=p.read_bytes()
        item["cache_hit"]=True
    else:
        req=urllib.request.Request(item["media_url"],headers={"User-Agent":"HSI-Open-Corpus/1.0"})
        with urllib.request.urlopen(req,timeout=60) as r:
            raw=r.read(MAX_BYTES+1)
        if len(raw)>MAX_BYTES:raise ValueError("source exceeds HSI_CORPUS_MAX_BYTES")
        p.write_bytes(raw);item["cache_hit"]=False
    item["raw_sha256"]=hashlib.sha256(raw).hexdigest()
    item["raw_bytes"]=len(raw)
    return p

def sample_to_float(path,max_seconds=30):
    with wave.open(str(path),"rb") as w:
        ch=w.getnchannels();sw=w.getsampwidth();sr=w.getframerate()
        n=min(w.getnframes(),int(sr*max_seconds))
        comp=w.getcomptype()
        if comp!="NONE":raise ValueError("compressed WAV not supported")
        if ch<1 or ch>8 or sw not in (1,2,3,4) or sr<4000:raise ValueError("unsupported WAV format")
        raw=w.readframes(n)
    frame_bytes=sw*ch;count=len(raw)//frame_bytes
    mono=array("f")
    for i in range(count):
        base=i*frame_bytes;s=0.0
        for c in range(ch):
            j=base+c*sw;b=raw[j:j+sw]
            if sw==1:v=(b[0]-128)/128.0
            elif sw==2:v=struct.unpack_from("<h",b)[0]/32768.0
            elif sw==3:
                u=b[0]|(b[1]<<8)|(b[2]<<16)
                if u&0x800000:u-=1<<24
                v=u/8388608.0
            else:v=struct.unpack_from("<i",b)[0]/2147483648.0
            s+=v
        mono.append(s/ch)
    if not mono:raise ValueError("empty WAV")
    return mono,sr

def resample(src,in_sr,out_sr,rate=1.0):
    # rate>1 plays faster/higher; deterministic linear interpolation, no ML/AI.
    step=(in_sr/out_sr)*rate
    n=max(1,int(len(src)/step))
    out=array("f",[0.0])*n
    for i in range(n):
        x=i*step;j=int(x)
        if j>=len(src)-1:out[i]=src[-1];continue
        f=x-j;out[i]=src[j]*(1-f)+src[j+1]*f
    return out

def write_wav(path,left,right,sr):
    peak=max(1.0,max((abs(x) for x in left),default=0),max((abs(x) for x in right),default=0))
    gain=.94/peak
    pcm=array("h")
    for l,r in zip(left,right):
        pcm.append(int(max(-1,min(1,math.tanh(l*gain)))*32767))
        pcm.append(int(max(-1,min(1,math.tanh(r*gain)))*32767))
    if sys.byteorder!="little":pcm.byteswap()
    with wave.open(str(path),"wb") as w:
        w.setnchannels(2);w.setsampwidth(2);w.setframerate(sr);w.writeframes(pcm.tobytes())

def render(items,text,out):
    basis=e257(text.encode("utf-8"));rng=PRNG(basis)
    seconds=18+(rng.pick(23))
    total=int(seconds*TARGET_SR)
    left=array("f",[0.0])*total;right=array("f",[0.0])*total
    events=[]
    decoded=[]
    for item in items:
        try:
            p=download(item);audio,sr=sample_to_float(p,30)
            decoded.append((item,audio,sr))
        except Exception as e:
            item["rejected_reason"]=str(e)
            print("source-warning>",item.get("title") or item["openverse_id"],str(e),file=sys.stderr)
    if not decoded:raise SystemExit("no usable CC0/PDM WAV sources found")
    event_count=max(len(decoded)*2,5+rng.pick(7))
    for ei in range(event_count):
        item,audio,sr=decoded[rng.pick(len(decoded))]
        rate=.84+rng.unit()*.34
        shifted=resample(audio,sr,TARGET_SR,rate)
        frag_sec=1.5+rng.unit()*5.5
        frag_n=min(len(shifted),int(frag_sec*TARGET_SR))
        if frag_n<1000:continue
        src_start=0 if len(shifted)==frag_n else rng.pick(len(shifted)-frag_n)
        dst_start=rng.pick(max(1,total-frag_n))
        pan=rng.unit()*2-1
        lg=math.sqrt((1-pan)*.5)*(.20+.20*rng.unit())
        rg=math.sqrt((1+pan)*.5)*(.20+.20*rng.unit())
        fade=min(int(.18*TARGET_SR),frag_n//4)
        for j in range(frag_n):
            env=1.0
            if fade:
                if j<fade:env=j/fade
                elif j>=frag_n-fade:env=(frag_n-1-j)/fade
            v=shifted[src_start+j]*env
            k=dst_start+j
            left[k]+=v*lg;right[k]+=v*rg
        events.append({
            "source_id":item["openverse_id"],"dst_start_seconds":round(dst_start/TARGET_SR,4),
            "fragment_seconds":round(frag_n/TARGET_SR,4),"playback_rate":round(rate,6),
            "pan":round(pan,6),"left_gain":round(lg,6),"right_gain":round(rg,6)
        })
    if not events:raise SystemExit("no render events")
    # finite traditional DSP: short feed-forward stereo delay.
    delay=int((.11+.19*rng.unit())*TARGET_SR);feedback=.07+.11*rng.unit()
    for i in range(delay,total):
        left[i]+=right[i-delay]*feedback
        right[i]+=left[i-delay]*feedback
    wav=out/"song.wav";write_wav(wav,left,right,TARGET_SR)
    return wav,basis,seconds,events,decoded

def write_e257(path,raw,chunk=512):
    ok=True;n=0
    with open(path,"w",encoding="utf-8") as f:
        f.write("[")
        first=True
        for i in range(0,len(raw),chunk):
            b=raw[i:i+chunk];x=e257(b);ok=ok and d257(x)==b
            if not first:f.write(",")
            f.write(str(x));first=False;n+=1
        f.write("]\n")
    return n,ok

def main():
    ap=argparse.ArgumentParser(description="HSI Open-Corpus Renderer — no AI, CC0/PDM WAV retrieval + deterministic DSP")
    ap.add_argument("keywords",nargs="*")
    ap.add_argument("--out",default=os.getenv("HSI_OUT"))
    ap.add_argument("--lock",default=LOCK_ENV)
    a=ap.parse_args()
    text=" ".join(a.keywords).strip()
    if not text:text=input("keywords> ").strip()
    if not text:raise SystemExit("keywords required")
    out=Path(a.out).expanduser() if a.out else Path.home()/"Music"/"HSI-Corpus"/(time.strftime("%Y%m%d-%H%M%S")+"-"+str(os.getpid()))
    out.mkdir(parents=True,exist_ok=True)
    print("protocol>",PROTOCOL);print("output>",out)
    print("ai> false")
    print("youtube_audio_used> false")

    if a.lock:
        lock=json.loads(Path(a.lock).expanduser().read_text(encoding="utf-8"))
        items=lock.get("sources") or []
        search_cert=lock.get("search_certificate") or {
            "protocol":"HSI-SEARCH/1.0","status":"UNRESOLVED","query":text,
            "epistemic_rule":"absence_of_retrieval_is_not_evidence_of_nonexistence",
            "reason":"legacy_lock_without_search_certificate"
        }
        print("corpus> locked",len(items))
    else:
        items,search_cert=discover(text)
        print("search_status>",search_cert.get("status"))
        print("search_uid>",search_cert.get("search_uid"))
        print("corpus> discovered",len(items))
    (out/"search.hsicert").write_text(canon(search_cert)+"\n",encoding="utf-8")
    if not items:
        status=search_cert.get("status","UNRESOLVED")
        raise SystemExit("HSI SEARCH "+status+": no admitted Openverse CC0/PDM WAV evidence within finite search budget")

    wav,basis,seconds,events,decoded=render(items,text,out)
    used_ids={e["source_id"] for e in events}
    used=[i for i,_,_ in decoded if i["openverse_id"] in used_ids]
    lock={
        "protocol":"HSI-OPEN-CORPUS-LOCK/1.0",
        "runtime_input":text,
        "generation_basis_e257":basis,
        "sources":used,
        "license_filter":["cc0","pdm"],
        "format_filter":["wav"],
        "youtube_audio_used":False,
        "search_protocol":"HSI-SEARCH/1.0",
        "search_uid":search_cert.get("search_uid"),
        "search_status":search_cert.get("status"),
        "search_certificate":search_cert
    }
    (out/"corpus.lock.json").write_text(canon(lock)+"\n",encoding="utf-8")
    (out/"events.json").write_text(canon(events)+"\n",encoding="utf-8")
    (out/"keywords.txt").write_text(text+"\n",encoding="utf-8")

    raw=wav.read_bytes();chunks=0;eok=True
    if E257_ENABLED:chunks,eok=write_e257(out/"song.e257",raw)
    checks={
        "wav":raw[:4]==b"RIFF" and raw[8:12]==b"WAVE",
        "audio_nonempty":len(raw)>1024,
        "keywords_roundtrip":d257(basis)==text.encode("utf-8"),
        "e257_audio_roundtrip":eok,
        "sources_present":len(used)>0,
        "all_indexed_cc0_or_pdm":all(str(x.get("license","")).lower() in ALLOWED_LICENSES for x in used),
        "all_wav":all(str(x.get("filetype","")).lower()=="wav" for x in used),
        "no_ai":True,
        "youtube_audio_unused":True
    }
    technical_closed=int(all(checks.values()))
    rights_closed=int(RIGHTS_ATTESTED and all(x.get("landing_url") for x in used))
    provenance=[{
        "openverse_id":x.get("openverse_id"),"title":x.get("title"),"creator":x.get("creator"),
        "license":x.get("license"),"license_version":x.get("license_version"),
        "media_url":x.get("media_url"),"landing_url":x.get("landing_url"),
        "provider":x.get("provider"),"source":x.get("source"),
        "raw_sha256":x.get("raw_sha256"),"raw_bytes":x.get("raw_bytes"),
        "license_basis":"OPENVERSE_INDEX_METADATA",
        "license_independently_verified":bool(RIGHTS_ATTESTED)
    } for x in used]
    cert={
        "protocol":PROTOCOL,"version":VERSION,
        "generation_input":"runtime-keywords-only",
        "generation_basis_e257":basis,
        "renderer":"open-corpus-retrieval-dsp",
        "ai_model":False,"neural_renderer":False,"machine_learning":False,
        "youtube_audio_used":False,
        "corpus_provider":"Openverse API",
        "search_protocol":"HSI-SEARCH/1.0",
        "search_uid":search_cert.get("search_uid"),
        "search_status":search_cert.get("status"),
        "search_epistemic_rule":search_cert.get("epistemic_rule"),
        "license_filter":["cc0","pdm"],"format_filter":["wav"],
        "license_assurance":"USER_ATTESTED" if RIGHTS_ATTESTED else "OPENVERSE_INDEX_ASSERTED_NOT_INDEPENDENTLY_VERIFIED",
        "rights_review_recommended":not RIGHTS_ATTESTED,
        "technical_closed":technical_closed,
        "rights_closed":rights_closed,
        "closed":technical_closed,
        "sample_rate":TARGET_SR,"channels":2,"duration_seconds":seconds,
        "source_count":len(provenance),"event_count":len(events),
        "audio_bytes":len(raw),"audio_sha256":hashlib.sha256(raw).hexdigest(),
        "e257_enabled":E257_ENABLED,"e257_chunk_bytes":512 if E257_ENABLED else 0,"e257_chunks":chunks,
        "blue_care":{
            "protocol":BLUE_PROTOCOL,
            "ideal":"PLEIADIAN-BLUE",
            "role":"provenance-license-truthfulness-not-creative-conditioning",
            "semantic_non_coercion":True,
            "license_uncertainty_preserved":not RIGHTS_ATTESTED,
            "human_override":True
        },
        "checks":checks,"sources":provenance
    }
    (out/"song.hsicert").write_text(canon(cert)+"\n",encoding="utf-8")
    files=["keywords.txt","search.hsicert","corpus.lock.json","events.json","song.wav","song.hsicert"]
    if E257_ENABLED:files.append("song.e257")
    (out/"manifest.json").write_text(canon({"protocol":PROTOCOL,"output":str(out),"files":files,"closed":technical_closed,"rights_closed":rights_closed})+"\n",encoding="utf-8")
    print("audio>",wav);print("sources>",len(provenance));print("events>",len(events))
    print("technical_closed>",technical_closed);print("rights_closed>",rights_closed)
    if not RIGHTS_ATTESTED:
        print("rights> Openverse-index metadata only; independently verify source landing pages before publication/commercial reuse")
    raise SystemExit(0 if technical_closed else 3)

if __name__=="__main__":main()
