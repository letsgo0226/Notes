#!/usr/bin/env python3
import argparse,json,math,os,re,sys,time,wave,hashlib
from array import array
from pathlib import Path

PROTOCOL="HSI-NATIVE-FIELD/1.0"
VERSION="2.0.0"
BLUE=b"PLEIADIAN-BLUE"
MASK=(1<<64)-1
if hasattr(sys,"set_int_max_str_digits"): sys.set_int_max_str_digits(0)

def e257(data):
    n=1
    for b in data:n=n*257+b+1
    return n

def d257(n):
    a=bytearray()
    while n>1:
        n,r=divmod(n,257)
        if not 1<=r<=256:raise ValueError("invalid E257")
        a.append(r-1)
    a.reverse();return bytes(a)

def canon(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":"))

def fold64(n):
    x=0x9E3779B97F4A7C15
    while n:
        x^=n&MASK
        x=((x<<27)|(x>>37))&MASK
        x=(x*0x94D049BB133111EB)&MASK
        n>>=64
    return x or 1

class Field:
    def __init__(self,n):self.x=fold64(n)
    def u64(self):
        self.x=(self.x+0x9E3779B97F4A7C15)&MASK
        z=self.x;z=(z^(z>>30))*0xBF58476D1CE4E5B9&MASK
        z=(z^(z>>27))*0x94D049BB133111EB&MASK
        return (z^(z>>31))&MASK
    def unit(self):return self.u64()/float(1<<64)
    def pick(self,n):return self.u64()%n
    def between(self,a,b):return a+self.pick(b-a+1)

def cjk(s):return any("\u3400"<=c<="\u9fff" for c in s)

def tokens(text):
    if cjk(text):
        p=[x for x in re.split(r"[\s,，、;；|/]+",text) if x]
        if len(p)==1 and len(p[0])>4:p=[c for c in p[0] if not c.isspace()]
        return p
    p=re.findall(r"[A-Za-z0-9][A-Za-z0-9'_-]*",text)
    return p or [x for x in text.split() if x] or [text]

def rotate(a,k):
    if not a:return a
    k%=len(a);return a[k:]+a[:k]

def field_text(src,f):
    base=tokens(src);nsec=2+f.pick(5);sections=[];lines=[]
    for si in range(nsec):
        nlines=2+f.pick(5);part=[]
        for li in range(nlines):
            take=1+f.pick(min(6,max(1,len(base)+2)))
            seq=rotate(base,f.pick(len(base)))
            out=[]
            for j in range(take):
                tok=seq[(j+f.pick(len(seq)))%len(seq)]
                if f.pick(5)==0 and len(tok)>1:
                    cut=1+f.pick(len(tok));tok=tok[:cut]
                out.append(tok)
            if f.pick(4)==0:out=out[::-1]
            line=("".join(out) if cjk(src) else " ".join(out)).strip()
            if line:part.append(line);lines.append(line)
        sections.append({"id":si+1,"lines":part})
    rendered="\n\n".join("[S%d]\n%s"%(s["id"],"\n".join(s["lines"])) for s in sections)
    return rendered,sections,lines

def pitch_set(f):
    count=5+f.pick(4);pcs={0}
    while len(pcs)<count:pcs.add(1+f.pick(11))
    return sorted(pcs)

def midi_hz(n):return 440.0*(2.0**((n-69)/12.0))

def harmonic_profile(f,n=None):
    n=n or (3+f.pick(8));a=[]
    for h in range(1,n+1):
        raw=.08+.92*f.unit()
        a.append(raw/(h**(.55+1.25*f.unit())))
    s=sum(a) or 1
    return [x/s for x in a]

def derive_score(field_n,f,sections,override_bpm=None,override_bars=None):
    pcs=pitch_set(f);tonic=36+f.pick(25);meter=3+f.pick(5);subdiv=1+f.pick(4)
    bpm=int(override_bpm or (68+f.pick(91)))
    secbars=[2+f.pick(7) for _ in sections]
    bars=sum(secbars)
    if override_bars:
        bars=max(4,min(96,int(override_bars)))
        q,r=divmod(bars,len(secbars));secbars=[q+(1 if i<r else 0) for i in range(len(secbars))]
    chord_size=2+f.pick(min(4,len(pcs)-1))
    root=0;chords=[];melody=[];rhythm=[]
    for bar in range(bars):
        root=(root+1+f.pick(len(pcs)-1))%len(pcs)
        chord=[]
        jump=1+f.pick(max(1,len(pcs)-1))
        for j in range(chord_size):
            idx=(root+j*jump)%len(pcs);octv=(root+j*jump)//len(pcs)
            chord.append(tonic+pcs[idx]+12*octv)
        chords.append(chord)
        slots=meter*subdiv
        density=1+f.pick(slots)
        onset=sorted(set(f.pick(slots) for _ in range(density*2)))[:density]
        if not onset:onset=[0]
        rhythm.append(onset)
        pos=f.pick(len(pcs))
        for slot in onset:
            step=f.pick(5)-2;pos=(pos+step)%len(pcs)
            octv=1+f.pick(3)
            melody.append({"bar":bar,"slot":slot,"note":tonic+pcs[pos]+12*octv,"gate":.45+.5*f.unit()})
    return {
        "generation_basis_e257":field_n,"pitch_classes":pcs,"tonic_midi":tonic,"meter":meter,"subdivision":subdiv,
        "bpm":bpm,"section_bars":secbars,"bars":bars,"chord_size":chord_size,"chords":chords,"rhythm":rhythm,
        "melody":melody,"harmonics":{"harmonic":harmonic_profile(f),"low":harmonic_profile(f),"voice":harmonic_profile(f)},
        "space":{"delay_beats":.20+.80*f.unit(),"feedback":.05+.24*f.unit()},
        "dynamics":{"harmonic":.025+.055*f.unit(),"low":.035+.075*f.unit(),"voice":.10+.13*f.unit(),"pulse":.03+.10*f.unit()}
    }

def add_harmonic(buf,sr,start,dur,freq,amp,profile,attack,release):
    a=int(start*sr);n=min(int(dur*sr),len(buf)-a)
    if n<=0 or freq<=0:return
    for i in range(n):
        t=i/sr;env=min(1.0,t/max(attack,1e-4),(dur-t)/max(release,1e-4))
        if env<=0:continue
        ph=2*math.pi*freq*t
        v=sum(w*math.sin((h+1)*ph) for h,w in enumerate(profile))
        buf[a+i]+=amp*env*v

def token_spectrum(tok,base_profile):
    n=e257(tok.encode("utf-8"));f1=220+(n%760);f2=780+((n//257)%2200);bw1=140+((n//(257**2))%420);bw2=260+((n//(257**3))%760)
    out=[]
    for h,w in enumerate(base_profile,1):
        hf=h*180.0
        shape=.12+math.exp(-((hf-f1)/bw1)**2)+.75*math.exp(-((hf-f2)/bw2)**2)
        out.append(w*shape)
    s=sum(out) or 1
    return [x/s for x in out],n

def add_voice(buf,sr,start,dur,freq,amp,profile,tok):
    p,n=token_spectrum(tok,profile);a=int(start*sr);m=min(int(dur*sr),len(buf)-a)
    if m<=0:return
    vib_hz=3.4+(n%37)/10.0;vib_depth=.0015+((n//37)%35)/10000.0
    trem=.02+((n//1291)%16)/100.0
    for i in range(m):
        t=i/sr;env=min(1.0,t/.025,(dur-t)/.09)
        if env<=0:continue
        phase=2*math.pi*freq*t*(1+vib_depth*math.sin(2*math.pi*vib_hz*t))
        v=sum(w*math.sin((h+1)*phase) for h,w in enumerate(p))
        v*=1-trem+trem*math.sin(2*math.pi*(1.2+(n%11)/7)*t)**2
        buf[a+i]+=amp*env*v

def add_pulse(buf,sr,start,field_word,amp):
    a=int(start*sr);dur=.025+((field_word>>8)&255)/1500.;m=min(int(dur*sr),len(buf)-a)
    freq=38+(field_word%310);decay=18+((field_word>>16)%70)
    s=(field_word or 1)&MASK
    for i in range(max(0,m)):
        t=i/sr;s^=(s<<13)&MASK;s^=s>>7;s^=(s<<17)&MASK
        noise=((s&65535)/32767.5)-1
        tonal=math.sin(2*math.pi*freq*t)
        mix=((field_word>>24)&255)/255
        buf[a+i]+=amp*math.exp(-decay*t)*(mix*noise+(1-mix)*tonal)

def render(score,text_lines,field_n,sr):
    beat=60.0/score["bpm"];total=score["bars"]*score["meter"]*beat
    buf=array("f",[0.0])*int(total*sr);f=Field(field_n^0xD1B54A32D192ED03)
    hp=score["harmonics"];dyn=score["dynamics"]
    for bar,ch in enumerate(score["chords"]):
        st=bar*score["meter"]*beat
        for note in ch:add_harmonic(buf,sr,st,score["meter"]*beat,midi_hz(note+12),dyn["harmonic"],hp["harmonic"],.08+.22*f.unit(),.12+.30*f.unit())
        root=ch[0]-12
        for q in range(max(1,score["meter"]//2)):
            add_harmonic(buf,sr,st+q*2*beat,min(2*beat,score["meter"]*beat-q*2*beat),midi_hz(root),dyn["low"],hp["low"],.01,.08)
        for slot in range(score["meter"]*score["subdivision"]):
            if slot in score["rhythm"][bar] or f.pick(5)==0:
                add_pulse(buf,sr,st+slot*(beat/score["subdivision"]),f.u64(),dyn["pulse"])
    toks=tokens(" ".join(text_lines)) or ["_"]
    for i,m in enumerate(score["melody"]):
        st=(m["bar"]*score["meter"]+m["slot"]/score["subdivision"])*beat
        dur=(beat/score["subdivision"])*m["gate"]
        add_voice(buf,sr,st,dur,midi_hz(m["note"]),dyn["voice"],hp["voice"],toks[i%len(toks)])
    delay=max(1,int(score["space"]["delay_beats"]*beat*sr));fb=score["space"]["feedback"]
    for i in range(delay,len(buf)):buf[i]+=fb*buf[i-delay]
    peak=max((abs(x) for x in buf),default=1.0);gain=.91/max(.91,peak)
    pcm=array("h",(int(max(-1,min(1,math.tanh(x*gain*1.15)/math.tanh(1.15)))*32767) for x in buf))
    if sys.byteorder!="little":pcm.byteswap()
    return pcm,total

def write_wav(path,pcm,sr):
    with wave.open(str(path),"wb") as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr);w.writeframes(pcm.tobytes())

def write_e257(path,raw,chunk=128):
    blocks=[e257(raw[i:i+chunk]) for i in range(0,len(raw),chunk)]
    path.write_text(json.dumps(blocks,separators=(",",":")),encoding="utf-8")
    return blocks,b"".join(d257(x) for x in blocks)==raw

def build(keywords,out=None,sr=24000,bpm=None,bars=None):
    kb=keywords.encode("utf-8");field_n=e257(kb);f=Field(field_n)
    lyric_text,sections,lines=field_text(keywords,f)
    score=derive_score(field_n,f,sections,bpm,bars)
    out=Path(out).expanduser() if out else Path.home()/"Music"/"HSI"/(time.strftime("%Y%m%d-%H%M%S")+"-"+str(os.getpid()))
    out.mkdir(parents=True,exist_ok=True)
    (out/"keywords.txt").write_text(keywords+"\n",encoding="utf-8")
    (out/"lyrics.txt").write_text(lyric_text+"\n",encoding="utf-8")
    (out/"score.json").write_text(canon({"protocol":PROTOCOL,"keywords":keywords,"sections":sections,**score})+"\n",encoding="utf-8")
    print("protocol>",PROTOCOL);print("output>",out)
    print("field>",score["bars"],"bars,",score["meter"],"/4-like pulse,",score["bpm"],"BPM,",len(score["pitch_classes"]),"pitch classes")
    pcm,duration=render(score,lines,field_n,sr);wavp=out/"song.wav";write_wav(wavp,pcm,sr);raw=wavp.read_bytes()
    blocks,closed=write_e257(out/"song.e257",raw)
    checks={
        "wav":raw[:4]==b"RIFF" and raw[8:12]==b"WAVE",
        "e257_reconstructs_audio":closed,
        "keywords_roundtrip":d257(field_n)==kb,
        "blue_roundtrip":d257(e257(BLUE))==BLUE,
        "blue_not_generation_seed":field_n!=e257(BLUE)
    }
    cert={
        "protocol":PROTOCOL,"version":VERSION,"renderer":"HSI-native-field","external_ai":False,"external_api":False,
        "creative_presets":[],"generation_input":"runtime-keywords-only","generation_basis_e257":field_n,
        "blue_e257":e257(BLUE),"blue_role":"certificate-normative-only","blue_conditioning":False,"sample_rate":sr,
        "derived":{"bars":score["bars"],"bpm":score["bpm"],"meter":score["meter"],"subdivision":score["subdivision"],"pitch_classes":score["pitch_classes"],"tonic_midi":score["tonic_midi"],"section_bars":score["section_bars"],"chord_size":score["chord_size"]},
        "duration_seconds":round(duration,3),"audio_bytes":len(raw),"e257_chunk_bytes":128,"e257_chunks":len(blocks),
        "audio_sha256":hashlib.sha256(raw).hexdigest(),"checks":checks
    }
    cert["closed"]=int(all(checks.values()))
    (out/"song.hsicert").write_text(canon(cert)+"\n",encoding="utf-8")
    manifest={"protocol":PROTOCOL,"output":str(out),"files":["keywords.txt","lyrics.txt","score.json","song.wav","song.e257","song.hsicert"],"closed":cert["closed"]}
    (out/"manifest.json").write_text(canon(manifest)+"\n",encoding="utf-8")
    print("audio>",wavp);print("seconds>","%.2f"%duration);print("e257_chunks>",len(blocks));print("closed>",cert["closed"])
    return out,cert

def main():
    p=argparse.ArgumentParser(description="HSI Native Generative Field — zero content presets, local synthesis")
    p.add_argument("keywords",nargs="*")
    p.add_argument("--out",default=os.getenv("HSI_OUT"))
    p.add_argument("--sr",type=int,default=int(os.getenv("HSI_SR","24000")))
    p.add_argument("--bpm",type=int,default=int(os.getenv("HSI_BPM","0")) or None)
    p.add_argument("--bars",type=int,default=int(os.getenv("HSI_BARS","0")) or None)
    a=p.parse_args();q=" ".join(a.keywords).strip()
    if not q:q=input("keywords> ").strip()
    if not q:raise SystemExit("keywords required")
    sr=max(8000,min(48000,a.sr));_,cert=build(q,a.out,sr,a.bpm,a.bars)
    raise SystemExit(0 if cert["closed"] else 3)

if __name__=="__main__":main()
