#!/usr/bin/env python3
import argparse, hashlib, json, math, os, random, struct, sys, time, urllib.request, wave
from array import array
from pathlib import Path
from hsi_search import run_search, VERSION as HSI_SEARCH_VERSION

PROTOCOL="HSI-OPEN-CORPUS/1.0"
CORRESPONDENCE_PROTOCOL="HSI-RC/1.0"
BLUE_PROTOCOL="HSI-PLEIADIAN-BLUE-CARE/1.0"
VERSION="1.8.0"
MIN_HSI_SEARCH_VERSION=(1,4,0)

def _semver_tuple(v):
    try:
        return tuple(int(x) for x in str(v).split(".")[:3])
    except Exception:
        return (0,0,0)

if _semver_tuple(HSI_SEARCH_VERSION) < MIN_HSI_SEARCH_VERSION:
    raise SystemExit(
        "HSI version mismatch: Open-Corpus %s requires HSI-SEARCH >= 1.4.0; got %s. "
        "Rerun the public launcher so both components are refreshed together."
        % (VERSION, HSI_SEARCH_VERSION)
    )
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
RC_ENABLED=os.getenv("HSI_CORRESPONDENCE","1")!="0"
RC_MAX_CANDIDATES=max(0,int(os.getenv("HSI_RC_MAX_CANDIDATES","0")))
RC_PROFILE={
    "rms":(float(os.getenv("HSI_RC_RMS_MIN",".025")),float(os.getenv("HSI_RC_RMS_MAX",".30"))),
    "peak":(float(os.getenv("HSI_RC_PEAK_MIN",".15")),float(os.getenv("HSI_RC_PEAK_MAX",".90"))),
    "crest":(float(os.getenv("HSI_RC_CREST_MIN","1.1")),float(os.getenv("HSI_RC_CREST_MAX","12"))),
    "silence_ratio":(0.0,float(os.getenv("HSI_RC_SILENCE_MAX",".85"))),
    "stereo_balance":(0.0,float(os.getenv("HSI_RC_BALANCE_MAX",".55"))),
    "clip_ratio":(0.0,float(os.getenv("HSI_RC_CLIP_MAX","0")))
}
RC_PRIMES={"rms":2,"peak":3,"crest":5,"silence_ratio":7,"stereo_balance":11,"clip_ratio":13}
ALLOWED_LICENSES={"cc0","pdm"}
ALLOWED_CATEGORIES={"music","sound_effect"}

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


def music_source_reasons(item):
    reasons=[]
    cat=str(item.get("category") or "").lower()
    meta=(" ".join([
        str(item.get("title") or ""),
        str(item.get("creator") or ""),
        str(item.get("creator_url") or ""),
        " ".join(str(t) for t in (item.get("tags") or []))
    ])).lower()
    title=str(item.get("title") or "")
    if cat not in ALLOWED_CATEGORIES:
        reasons.append("renderer_category_not_allowed")
    if cat in {"pronunciation","audiobook","podcast","news"}:
        reasons.append("renderer_spoken_word_category")
    if "lingualibre" in meta or title.startswith("LL-"):
        reasons.append("renderer_lexical_pronunciation_source")
    return reasons

def renderer_admit_sources(items):
    admitted=[];rejected=[]
    for item in items:
        reasons=music_source_reasons(item)
        if reasons:
            x=dict(item);x["renderer_rejection_reasons"]=reasons
            rejected.append(x)
            print("source-rejected>",item.get("title") or item.get("openverse_id"),",".join(reasons),file=sys.stderr)
        else:
            admitted.append(item)
    return admitted,rejected

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
    policy={
        "license_allow":["cc0","pdm"],
        "extension_allow":["wav"],
        "category_allow":["music","sound_effect"],
        "category_deny":["pronunciation","audiobook","podcast","news"],
        "source_prefer":["freesound"],
        "source_exclude":[]
    }
    budget={
        "max_results":MAX_ITEMS,
        "page_size":SEARCH_PAGE,
        "timeout_seconds":SEARCH_TIMEOUT,
        "retries":SEARCH_RETRIES,
        "max_calls":max(8,min(40,SEARCH_RETRIES*8))
    }
    cert=run_search(text,source="network_audio",policy=policy,budget=budget,base_url=API)
    items=[]
    for x in cert.get("results") or []:
        items.append({
            "source_id":x.get("record_uid"),
            "openverse_id":x.get("record_uid"),
            "source_adapter":x.get("source"),
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
            "selected_media_variant":x.get("selected_media_variant"),
            "primary_media_url":x.get("primary_media_url"),
            "primary_filetype":x.get("primary_filetype"),
            "alt_files":x.get("alt_files") or [],
            "category":x.get("category"),
            "genres":x.get("genres") or [],
            "tags":x.get("tags") or [],
            "query":x.get("matched_query"),
            "openverse_search_url":x.get("search_url"),
            "license_basis":x.get("assertion_basis"),
            "license_independently_verified":False
        })
    items,renderer_rejected=renderer_admit_sources(items)
    cert["renderer_admission"]={
        "required_search_version":">=1.4.0",
        "actual_search_version":HSI_SEARCH_VERSION,
        "admitted_after_renderer_gate":len(items),
        "rejected_after_renderer_gate":len(renderer_rejected),
        "rejected":renderer_rejected
    }
    if not items and cert.get("status")=="FOUND":
        cert["status"]="UNRESOLVED"
        cert["reason"]="search_found_only_sources_rejected_by_renderer_music_gate"
    return items,cert

def cache_path(item):
    safe="".join(c if c.isalnum() or c in "-_" else "_" for c in item["openverse_id"])
    # The byte budget is part of cache identity because large WAV sources may
    # intentionally be cached as a finite prefix rather than as the full file.
    return CACHE/(safe+"-"+str(MAX_BYTES)+".wav")

def _source_total_bytes(item,response=None):
    reported=item.get("filesize")
    try:
        if reported is not None and int(reported)>0:return int(reported)
    except Exception:
        pass
    if response is not None:
        cr=response.headers.get("Content-Range")
        if cr and "/" in cr:
            try:return int(cr.rsplit("/",1)[1])
            except Exception:pass
        cl=response.headers.get("Content-Length")
        try:
            if cl:return int(cl)
        except Exception:pass
    return None

def download(item):
    CACHE.mkdir(parents=True,exist_ok=True)
    p=cache_path(item)
    total=_source_total_bytes(item)
    if p.exists() and p.stat().st_size>44:
        raw=p.read_bytes()
        item["cache_hit"]=True
        item["download_mode"]="cache_prefix" if total and total>len(raw) else "cache_full"
    else:
        headers={
            "User-Agent":"HSI-Open-Corpus/1.7",
            "Range":"bytes=0-%d"%(MAX_BYTES-1)
        }
        req=urllib.request.Request(item["media_url"],headers=headers)
        with urllib.request.urlopen(req,timeout=60) as r:
            raw=r.read(MAX_BYTES)
            total=_source_total_bytes(item,r) or total
            status=getattr(r,"status",None)
        if len(raw)<=44:raise ValueError("source prefix is too small to contain WAV audio")
        p.write_bytes(raw);item["cache_hit"]=False
        item["download_http_status"]=status
        item["download_mode"]="prefix_range" if total and total>len(raw) else "full"
    item["source_total_bytes"]=total
    item["downloaded_bytes"]=len(raw)
    item["partial_source"]=bool(total and total>len(raw))
    item["raw_scope"]="downloaded_prefix" if item["partial_source"] else "full_source"
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

def audio_features(path):
    with wave.open(str(path),"rb") as w:
        if w.getnchannels()!=2 or w.getsampwidth()!=2:raise ValueError("quality verifier requires stereo 16-bit PCM WAV")
        sr=w.getframerate();frames=w.getnframes();raw=w.readframes(frames)
    pcm=array("h");pcm.frombytes(raw)
    if sys.byteorder!="little":pcm.byteswap()
    if frames<=0 or len(pcm)<2:raise ValueError("empty quality-verification WAV")
    ss_l=ss_r=0.0;peak=0.0;silent=clip=0
    for i in range(0,len(pcm)-1,2):
        li=pcm[i];ri=pcm[i+1];l=li/32768.0;r=ri/32768.0
        ss_l+=l*l;ss_r+=r*r;peak=max(peak,abs(l),abs(r))
        silent+=int(abs(l)<.01 and abs(r)<.01)
        clip+=int(abs(li)>=32760 or abs(ri)>=32760)
    rms_l=math.sqrt(ss_l/frames);rms_r=math.sqrt(ss_r/frames)
    rms=math.sqrt((ss_l+ss_r)/(2*frames))
    return {
        "rms":rms,"peak":peak,"crest":peak/max(rms,1e-12),
        "silence_ratio":silent/frames,
        "stereo_balance":abs(rms_l-rms_r)/max(rms_l,rms_r,1e-12),
        "clip_ratio":clip/frames,
        "duration_seconds":frames/sr
    }

def correspondence(features):
    terms={};residual=0.0
    for name,(lo,hi) in RC_PROFILE.items():
        x=float(features[name]);d=lo-x if x<lo else x-hi if x>hi else 0.0
        term=(d*d)/RC_PRIMES[name];terms[name]={"value":x,"range":[lo,hi],"distance":d,"prime":RC_PRIMES[name],"term":term}
        residual+=term
    return residual,terms,int(residual==0.0)

def render(items,text,out,candidate_index=0):
    seed_text=text if candidate_index==0 else text+"|candidate="+str(candidate_index)
    basis=e257(seed_text.encode("utf-8"));rng=PRNG(basis)
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
    print("versions> open_corpus="+VERSION+" hsi_search="+HSI_SEARCH_VERSION)
    print("ai> false")
    print("youtube_audio_used> false")

    if a.lock:
        lock=json.loads(Path(a.lock).expanduser().read_text(encoding="utf-8"))
        items=lock.get("sources") or []
        unsafe=[]
        for x in items:
            cat=str(x.get("category") or "").lower()
            textmeta=(" ".join([
                str(x.get("title") or ""),str(x.get("creator") or ""),
                str(x.get("creator_url") or "")," ".join(str(t) for t in (x.get("tags") or []))
            ])).lower()
            if cat not in ALLOWED_CATEGORIES or "lingualibre" in textmeta or str(x.get("title") or "").startswith("LL-"):
                unsafe.append(x.get("openverse_id") or x.get("title"))
        if unsafe:
            raise SystemExit("locked corpus rejected by HSI speech/category gate: "+",".join(str(x) for x in unsafe))
        items,locked_rejected=renderer_admit_sources(items)
        if locked_rejected:
            raise SystemExit("locked corpus rejected by renderer defense-in-depth gate")
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
        raise SystemExit("HSI SEARCH "+status+": no admitted network CC0/PDM WAV evidence within finite search budget")

    state_path=out/"correspondence.state.json"
    candidate_index=0
    if state_path.exists():
        try:candidate_index=max(0,int(json.loads(state_path.read_text(encoding="utf-8")).get("next_candidate",0)))
        except Exception:candidate_index=0
    while True:
        wav,basis,seconds,events,decoded=render(items,text,out,candidate_index)
        features=audio_features(wav)
        residual,rc_terms,rc_closed=correspondence(features)
        effective_rc_closed=int((not RC_ENABLED) or rc_closed)
        print("candidate>",candidate_index,"E_half>",format(residual,".12g"),"correspondence_closed>",effective_rc_closed)
        if effective_rc_closed:break
        candidate_index+=1
        tmp=state_path.with_suffix(".tmp")
        tmp.write_text(canon({"protocol":CORRESPONDENCE_PROTOCOL,"next_candidate":candidate_index,"last_residual":residual})+"\n",encoding="utf-8")
        os.replace(tmp,state_path)
        if RC_MAX_CANDIDATES and candidate_index>=RC_MAX_CANDIDATES:
            raise SystemExit("HSI RC UNRESOLVED: no candidate satisfied the endogenous correspondence profile within finite search budget")
    if state_path.exists():state_path.unlink()
    rc_cert={
        "protocol":CORRESPONDENCE_PROTOCOL,
        "model":"prime-weighted-nonnegative-residual-at-sigma-1/2",
        "sigma":"1/2",
        "candidate_index":candidate_index,
        "candidate_count":candidate_index+1,
        "profile":{k:list(v) for k,v in RC_PROFILE.items()},
        "features":features,
        "terms":rc_terms,
        "residual":residual,
        "closed":effective_rc_closed,
        "interpretation":"model correspondence certificate, not a Riemann-hypothesis claim"
    }
    (out/"correspondence.hsicert").write_text(canon(rc_cert)+"\n",encoding="utf-8")
    used_ids={e["source_id"] for e in events}
    used=[i for i,_,_ in decoded if i["openverse_id"] in used_ids]
    lock={
        "protocol":"HSI-OPEN-CORPUS-LOCK/1.0",
        "runtime_input":text,
        "generation_basis_e257":basis,
        "candidate_index":candidate_index,
        "correspondence_protocol":CORRESPONDENCE_PROTOCOL,
        "sources":used,
        "license_filter":["cc0","pdm"],
        "format_filter":["wav"],
        "wav_selection":"primary_or_openverse_alt_files",
        "source_preference":["openverse:freesound","wikimedia_commons_audio"],
        "category_filter":["music","sound_effect"],
        "speech_policy":"EXCLUDE_PRONUNCIATION_AUDIOBOOK_PODCAST_NEWS_AND_LINGUALIBRE_LEXICAL_CLIPS",
        "youtube_audio_used":False,
        "search_protocol":"HSI-SEARCH/1.0",
        "net_protocol":search_cert.get("net_protocol"),
        "net_projection_uid":(search_cert.get("net_projection") or {}).get("projection_uid"),
        "search_uid":search_cert.get("search_uid"),
        "search_status":search_cert.get("status"),
        "search_certificate":search_cert
    }
    (out/"corpus.lock.json").write_text(canon(lock)+"\n",encoding="utf-8")
    (out/"events.json").write_text(canon(events)+"\n",encoding="utf-8")
    (out/"keywords.txt").write_text(text+"\n",encoding="utf-8")

    raw=wav.read_bytes();chunks=0;eok=True
    if E257_ENABLED:chunks,eok=write_e257(out/"song.e257",raw)
    keyword_basis=e257(text.encode("utf-8"))
    seed_text=text if candidate_index==0 else text+"|candidate="+str(candidate_index)
    checks={
        "wav":raw[:4]==b"RIFF" and raw[8:12]==b"WAVE",
        "audio_nonempty":len(raw)>1024,
        "keywords_roundtrip":d257(keyword_basis)==text.encode("utf-8"),
        "generation_seed_roundtrip":d257(basis)==seed_text.encode("utf-8"),
        "e257_audio_roundtrip":eok,
        "sources_present":len(used)>0,
        "all_indexed_cc0_or_pdm":all(str(x.get("license","")).lower() in ALLOWED_LICENSES for x in used),
        "all_wav":all(str(x.get("filetype","")).lower()=="wav" for x in used),
        "all_music_or_sound_effect":all(str(x.get("category","")).lower() in ALLOWED_CATEGORIES for x in used),
        "no_lexical_pronunciation_sources":all(
            "lingualibre" not in (" ".join([
                str(x.get("title") or ""),str(x.get("creator") or ""),str(x.get("creator_url") or "")
            ])).lower()
            and not str(x.get("title") or "").startswith("LL-")
            for x in used
        ),
        "no_ai":True,
        "youtube_audio_unused":True
    }
    technical_closed=int(all(checks.values()))
    rights_closed=int(RIGHTS_ATTESTED and all(x.get("landing_url") for x in used))
    closed=int(technical_closed and effective_rc_closed)
    provenance=[{
        "openverse_id":x.get("openverse_id"),"title":x.get("title"),"creator":x.get("creator"),
        "license":x.get("license"),"license_version":x.get("license_version"),
        "media_url":x.get("media_url"),"landing_url":x.get("landing_url"),
        "provider":x.get("provider"),"source":x.get("source"),
        "selected_media_variant":x.get("selected_media_variant"),
        "primary_media_url":x.get("primary_media_url"),
        "primary_filetype":x.get("primary_filetype"),
        "category":x.get("category"),"genres":x.get("genres") or [],"tags":x.get("tags") or [],
        "source_total_bytes":x.get("source_total_bytes") or x.get("filesize"),
        "downloaded_bytes":x.get("downloaded_bytes") or x.get("raw_bytes"),
        "partial_source":bool(x.get("partial_source")),
        "download_mode":x.get("download_mode"),
        "raw_scope":x.get("raw_scope"),
        "raw_sha256":x.get("raw_sha256"),"raw_bytes":x.get("raw_bytes"),
        "license_basis":x.get("license_basis") or "ADAPTER_METADATA",
        "license_independently_verified":bool(RIGHTS_ATTESTED)
    } for x in used]
    cert={
        "protocol":PROTOCOL,"version":VERSION,
        "generation_input":"runtime-keywords-plus-candidate-index",
        "runtime_keywords_basis_e257":keyword_basis,
        "generation_basis_e257":basis,
        "candidate_index":candidate_index,
        "candidate_count":candidate_index+1,
        "correspondence":rc_cert,
        "renderer":"open-corpus-retrieval-dsp",
        "hsi_search_version":HSI_SEARCH_VERSION,
        "minimum_hsi_search_version":"1.4.0",
        "ai_model":False,"neural_renderer":False,"machine_learning":False,
        "youtube_audio_used":False,
        "corpus_provider":"HSI NET public audio adapters",
        "search_protocol":"HSI-SEARCH/1.0",
        "net_protocol":search_cert.get("net_protocol"),
        "net_projection_uid":(search_cert.get("net_projection") or {}).get("projection_uid"),
        "net_model":(search_cert.get("net_projection") or {}).get("model"),
        "search_uid":search_cert.get("search_uid"),
        "search_status":search_cert.get("status"),
        "search_epistemic_rule":search_cert.get("epistemic_rule"),
        "license_filter":["cc0","pdm"],"format_filter":["wav"],
        "wav_selection":"primary_or_openverse_alt_files_or_commons_wav",
        "large_wav_policy":"finite_prefix_up_to_HSI_CORPUS_MAX_BYTES",
        "max_download_bytes_per_source":MAX_BYTES,
        "source_preference":["openverse:freesound","wikimedia_commons_audio"],
        "category_filter":["music","sound_effect"],
        "speech_policy":"EXCLUDE_PRONUNCIATION_AUDIOBOOK_PODCAST_NEWS_AND_LINGUALIBRE_LEXICAL_CLIPS",
        "license_assurance":"USER_ATTESTED" if RIGHTS_ATTESTED else "OPENVERSE_INDEX_ASSERTED_NOT_INDEPENDENTLY_VERIFIED",
        "rights_review_recommended":not RIGHTS_ATTESTED,
        "technical_closed":technical_closed,
        "correspondence_closed":effective_rc_closed,
        "rights_closed":rights_closed,
        "closed":closed,
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
    files=["keywords.txt","search.hsicert","corpus.lock.json","events.json","correspondence.hsicert","song.wav","song.hsicert"]
    if E257_ENABLED:files.append("song.e257")
    (out/"manifest.json").write_text(canon({"protocol":PROTOCOL,"output":str(out),"files":files,"closed":closed,"technical_closed":technical_closed,"correspondence_closed":effective_rc_closed,"rights_closed":rights_closed})+"\n",encoding="utf-8")
    print("audio>",wav);print("sources>",len(provenance));print("events>",len(events))
    print("candidate_index>",candidate_index);print("E_half>",format(residual,".12g"))
    print("technical_closed>",technical_closed);print("correspondence_closed>",effective_rc_closed);print("rights_closed>",rights_closed)
    if not RIGHTS_ATTESTED:
        print("rights> adapter metadata only; independently verify source landing pages before publication/commercial reuse")
    raise SystemExit(0 if closed else 3)

if __name__=="__main__":main()
