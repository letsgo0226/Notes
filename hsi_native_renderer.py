#!/usr/bin/env python3
import argparse, hashlib, json, math, os, re, sys, time, wave
from array import array
from pathlib import Path

PROTOCOL="HSI-NATIVE-RENDER/1.0"
BLUE=b"PLEIADIAN-BLUE"
VERSION="1.0.0"
if hasattr(sys,"set_int_max_str_digits"): sys.set_int_max_str_digits(0)

def e257(data):
    n=1
    for b in data: n=n*257+b+1
    return n

def d257(n):
    out=bytearray()
    while n>1:
        n,r=divmod(n,257)
        if r<1: raise ValueError("invalid E257 digit")
        out.append(r-1)
    out.reverse()
    return bytes(out)

def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":"))

class PRNG:
    def __init__(self,seed): self.x=(seed or 0x9E3779B97F4A7C15)&((1<<64)-1)
    def u64(self):
        x=self.x
        x^=(x<<13)&((1<<64)-1); x^=x>>7; x^=(x<<17)&((1<<64)-1)
        self.x=x&((1<<64)-1); return self.x
    def rand(self): return self.u64()/float(1<<64)
    def choice(self,s): return s[self.u64()%len(s)]
    def randint(self,a,b): return a+self.u64()%(b-a+1)

def cjk(text): return any("\u3400"<=ch<="\u9fff" for ch in text)

def units(text):
    if cjk(text):
        p=[x for x in re.split(r"[\s,，、;；|/]+",text) if x]
        return p or [ch for ch in text if ch.strip()]
    p=re.findall(r"[A-Za-z0-9][A-Za-z0-9'_-]*",text)
    return p or [text.strip()]

def lyrics_for(keywords,rng):
    ks=units(keywords) or ["sound"]
    def k(i=0): return ks[(rng.randint(0,10000)+i)%len(ks)]
    if cjk(keywords):
        vt=["{0}沿著夜色慢慢發亮","我在{0}與{1}之間聽見回聲","如果{0}仍記得{1}","讓{0}穿過還沒有名字的風","{0}不是答案卻成為方向","我們把{0}留在下一個清晨","當{0}靠近{1}，時間忽然安靜","我把{0}寫進尚未完成的歌"]
        ch=["讓{0}再一次靠近","讓{1}穿過漫長的夜","所有未完成的{0}","都在此刻向{1}回答"]
        br=["即使道路仍然未知","{0}也不必成為命令","只要{1}仍允許彼此選擇","我們就能重新開始"]
    else:
        vt=["{0} is glowing at the edge of night","I hear {0} moving through {1}","If {0} still remembers {1}","Let {0} cross the unnamed wind","{0} is not an answer, only a direction","We leave {0} for the coming dawn","When {0} meets {1}, the hours become still","I write {0} into an unfinished song"]
        ch=["Let {0} come close again","Let {1} travel through the night","Every unfinished {0}","Turns toward {1} in the light"]
        br=["Even when the road is still unknown","{0} never has to become a command","As long as {1} leaves room to choose","We can begin again"]
    v1=[rng.choice(vt).format(k(i),k(i+1)) for i in range(4)]
    v2=[rng.choice(vt).format(k(i+4),k(i+5)) for i in range(4)]
    chorus=[x.format(k(i+8),k(i+9)) for i,x in enumerate(ch)]
    bridge=[x.format(k(i+12),k(i+13)) for i,x in enumerate(br)]
    sections=[("VERSE I",v1),("CHORUS",chorus),("VERSE II",v2),("BRIDGE",bridge),("FINAL CHORUS",chorus)]
    return "\n\n".join("["+name+"]\n"+"\n".join(lines) for name,lines in sections),sections

SCALES={"major":[0,2,4,5,7,9,11],"minor":[0,2,3,5,7,8,10],"dorian":[0,2,3,5,7,9,10],"mixolydian":[0,2,4,5,7,9,10]}
def hz(n): return 440.0*(2.0**((n-69)/12.0))

def add_tone(buf,sr,start,dur,freq,amp,kind="sine",attack=.02,release=.08):
    a=int(start*sr); n=min(int(dur*sr),len(buf)-a)
    if n<=0 or freq<=0:return
    for i in range(n):
        t=i/sr; env=min(1.0,t/max(attack,1e-5),(dur-t)/max(release,1e-5))
        if env<0:env=0
        ph=2*math.pi*freq*t
        v=math.sin(ph)
        if kind=="bass": v+=.28*math.sin(2*ph)
        elif kind=="pad": v+=.20*math.sin(2*ph)+.09*math.sin(3*ph)
        buf[a+i]+=amp*env*v

VOWELS={"a":(800.,1150.),"e":(500.,1700.),"i":(300.,2200.),"o":(500.,900.),"u":(350.,800.)}
def vowel(token):
    low=token.lower()
    for v in "aeiou":
        if v in low:return v
    return "a" if cjk(token) else "e"

def add_voice(buf,sr,start,dur,freq,token,amp=.20):
    a=int(start*sr); n=min(int(dur*sr),len(buf)-a)
    if n<=0:return
    f1,f2=VOWELS[vowel(token)]; harms=[]
    for h in range(1,7):
        hf=h*freq; w=.18+math.exp(-((hf-f1)/420.)**2)+.70*math.exp(-((hf-f2)/650.)**2)
        harms.append(w/h)
    norm=max(sum(harms),1e-6); harms=[x/norm for x in harms]
    for i in range(n):
        t=i/sr; env=min(1.0,t/.035,(dur-t)/.10)
        if env<0:env=0
        vib=1.0+.004*math.sin(2*math.pi*5.2*t); ph=2*math.pi*freq*t*vib
        v=sum(w*math.sin(h*ph) for h,w in enumerate(harms,1))
        buf[a+i]+=amp*env*(v+.03*math.sin(2*math.pi*(freq*.51)*t))

def add_kick(buf,sr,start,amp=.34):
    a=int(start*sr); n=min(int(.24*sr),len(buf)-a)
    for i in range(max(n,0)):
        t=i/sr; f=95*math.exp(-8*t)+42
        buf[a+i]+=amp*math.exp(-14*t)*math.sin(2*math.pi*f*t)

def add_hat(buf,sr,start,rng,amp=.055):
    a=int(start*sr); n=min(int(.06*sr),len(buf)-a); s=rng.u64() or 1
    for i in range(max(n,0)):
        s^=(s<<13)&((1<<64)-1); s^=s>>7; s^=(s<<17)&((1<<64)-1)
        noise=((s&0xffff)/32767.5)-1.0
        buf[a+i]+=amp*math.exp(-55*(i/sr))*noise

def make_score(seed,rng,bars,bpm=None):
    mode=list(SCALES)[seed%len(SCALES)]; scale=SCALES[mode]; tonic=45+(seed%8); bpm=int(bpm or (96+(seed%29)))
    bank=[[0,5,3,4],[0,3,5,4],[0,4,5,3],[0,5,4,3]]; prog=bank[(seed>>8)%len(bank)]
    chords=[]; melody=[]
    for bar in range(bars):
        degree=prog[bar%len(prog)]; root=tonic+scale[degree%7]
        tri=[root,tonic+scale[(degree+2)%7]+(12 if degree+2>=7 else 0),tonic+scale[(degree+4)%7]+(12 if degree+4>=7 else 0)]
        chords.append(tri)
        for _ in range(4):
            d=(degree+rng.choice([0,1,2,4,5]))%7; octave=12 if rng.rand()>.18 else 0
            melody.append(tonic+24+scale[d]+octave)
    return {"mode":mode,"tonic_midi":tonic,"bpm":bpm,"bars":bars,"chords":chords,"melody":melody}

def render(score,lyric_text,seed,sr):
    beat=60.0/score["bpm"]; total=score["bars"]*4*beat; buf=array("f",[0.0])*int(total*sr)
    rng=PRNG(seed^0xA5A5A5A5A5A5A5A5)
    toks=units(re.sub(r"\[[^\]]+\]"," ",lyric_text)) or ["ah"]
    for bar,chord in enumerate(score["chords"]):
        st=bar*4*beat
        for note in chord:add_tone(buf,sr,st,4*beat,hz(note+12),.035,"pad",.18,.30)
        add_tone(buf,sr,st,2*beat,hz(chord[0]-12),.09,"bass",.01,.12)
        add_tone(buf,sr,st+2*beat,2*beat,hz(chord[0]-12),.075,"bass",.01,.12)
    for b in range(score["bars"]*4):
        t=b*beat; add_kick(buf,sr,t,.25 if b%4 in (0,2) else .13); add_hat(buf,sr,t+beat*.5,rng,.04)
    vi=0
    for i,note in enumerate(score["melody"]):
        bar=i//4
        if bar==0 or bar>=score["bars"]-1:continue
        add_voice(buf,sr,i*beat,beat*.88,hz(note),toks[vi%len(toks)],.18); vi+=1
    delay=int(sr*beat*.75)
    for i in range(delay,len(buf)):buf[i]+=.16*buf[i-delay]
    peak=max((abs(x) for x in buf),default=1.0); gain=.90/max(peak,.90); den=math.tanh(1.2)
    pcm=array("h",(int(max(-1,min(1,math.tanh(x*gain*1.2)/den))*32767) for x in buf))
    if sys.byteorder!="little":pcm.byteswap()
    return pcm,total

def write_wav(path,pcm,sr):
    with wave.open(str(path),"wb") as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr);w.writeframes(pcm.tobytes())

def write_e257(path,raw,chunk=128):
    blocks=[e257(raw[i:i+chunk]) for i in range(0,len(raw),chunk)]
    path.write_text(json.dumps(blocks,separators=(",",":")),encoding="utf-8")
    return blocks,b"".join(d257(n) for n in blocks)==raw

def build(keywords,out=None,bars=20,sr=22050,bpm=None):
    kb=keywords.encode(); seed=int.from_bytes(hashlib.sha256(kb).digest()[:8],"big"); rng=PRNG(seed)
    lyric_text,_=lyrics_for(keywords,rng); score=make_score(seed,rng,bars,bpm)
    out=Path(out).expanduser() if out else Path.home()/"Music"/"HSI"/(time.strftime("%Y%m%d-%H%M%S")+"-"+str(os.getpid()))
    out.mkdir(parents=True,exist_ok=True)
    print("protocol>",PROTOCOL); print("output>",out); print("render>",bars,"bars @",score["bpm"],"BPM,",score["mode"],",",sr,"Hz")
    (out/"keywords.txt").write_text(keywords+"\n",encoding="utf-8")
    (out/"lyrics.txt").write_text(lyric_text+"\n",encoding="utf-8")
    (out/"score.json").write_text(canon({"protocol":PROTOCOL,"keywords":keywords,"seed":seed,**score})+"\n",encoding="utf-8")
    pcm,duration=render(score,lyric_text,seed,sr); wavp=out/"song.wav"; write_wav(wavp,pcm,sr); raw=wavp.read_bytes()
    blocks,closed=write_e257(out/"song.e257",raw)
    cert={"protocol":PROTOCOL,"version":VERSION,"keywords_e257":e257(kb),"blue_e257":e257(BLUE),"seed":seed,"renderer":"HSI-native-procedural","external_ai":False,"external_api":False,"sample_rate":sr,"bars":bars,"bpm":score["bpm"],"duration_seconds":round(duration,3),"audio_bytes":len(raw),"e257_chunk_bytes":128,"e257_chunks":len(blocks),"audio_sha256":hashlib.sha256(raw).hexdigest(),"checks":{"wav":raw[:4]==b"RIFF" and raw[8:12]==b"WAVE","e257_reconstructs_audio":closed,"keywords_roundtrip":d257(e257(kb))==kb,"blue_roundtrip":d257(e257(BLUE))==BLUE}}
    cert["closed"]=int(all(cert["checks"].values())); (out/"song.hsicert").write_text(canon(cert)+"\n",encoding="utf-8")
    manifest={"protocol":PROTOCOL,"output":str(out),"files":["keywords.txt","lyrics.txt","score.json","song.wav","song.e257","song.hsicert"],"closed":cert["closed"]}
    (out/"manifest.json").write_text(canon(manifest)+"\n",encoding="utf-8")
    print("audio>",wavp); print("seconds>",f"{duration:.2f}"); print("e257_chunks>",len(blocks)); print("closed>",cert["closed"])
    return out,cert

def main():
    p=argparse.ArgumentParser(description="HSI Native Music Renderer — offline procedural song synthesis")
    p.add_argument("keywords",nargs="*"); p.add_argument("--out",default=os.getenv("HSI_OUT")); p.add_argument("--bars",type=int,default=int(os.getenv("HSI_BARS","20"))); p.add_argument("--sr",type=int,default=int(os.getenv("HSI_SR","22050"))); p.add_argument("--bpm",type=int,default=int(os.getenv("HSI_BPM","0")) or None)
    a=p.parse_args(); keywords=" ".join(a.keywords).strip()
    if not keywords:keywords=input("keywords> ").strip()
    if not keywords:raise SystemExit("keywords required")
    bars=max(4,min(a.bars,64)); sr=max(8000,min(a.sr,48000)); _,cert=build(keywords,a.out,bars,sr,a.bpm)
    raise SystemExit(0 if cert["closed"] else 3)

if __name__=="__main__":main()
