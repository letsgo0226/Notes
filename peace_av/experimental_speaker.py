#!/usr/bin/env python3
"""EXPERIMENTAL voice-energy driven original portrait animation.

A moving portrait is not filmed human performance or phoneme-accurate lip sync.
The output never claims that real political events or a real official occurred.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess

import cv2
import numpy as np
from PIL import Image

RATE = 16000

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def envelope(audio, seconds, fps):
    run = subprocess.run(
        ["ffmpeg","-nostdin","-loglevel","error","-i",str(audio),
         "-t",str(seconds),"-vn","-af","highpass=f=180,lowpass=f=2800",
         "-ar",str(RATE),"-ac","1","-f","f32le","pipe:1"],
        check=True, capture_output=True,
    )
    pcm=np.frombuffer(run.stdout,dtype="<f4")
    level=np.zeros(math.ceil(seconds*fps),dtype=np.float32)
    for i in range(len(level)):
        st=int(RATE*i/fps)
        chunk=pcm[st:st+int(RATE/fps)]
        if len(chunk):level[i]=np.sqrt(np.mean(chunk**2))
    noise=np.quantile(level,.23)
    hi=max(float(np.quantile(level,.88)),float(noise)+.003)
    level=np.clip((level-noise)/(hi-noise),0,1)
    result=np.zeros_like(level)
    for i,v in enumerate(level):
        last=result[i-1] if i else 0
        inertia=.41 if v>last else .66
        result[i]=last*inertia+v*(1-inertia)
    return result

def portrait(path, size):
    image=Image.open(path).convert("RGB")
    w,h=size; iw,ih=image.size
    if iw/ih>w/h:
        new_w=int(ih*w/h)
        image=image.crop(((iw-new_w)//2,0,(iw+new_w)//2,ih))
    else:
        new_h=int(iw*h/w)
        image=image.crop((0,(ih-new_h)//2,iw,(ih+new_h)//2))
    return cv2.cvtColor(np.array(image.resize(size,Image.Resampling.LANCZOS)),cv2.COLOR_RGB2BGR)

def frame(source,amount,n,fps,add_title=True):
    h,w=source.shape[:2]
    output=source.copy()
    # Fixed mouth calibration for the original generated 1672x941 image.
    cx,cy=round(816*w/1672),round(264*h/941)
    pw,ph=round(87*w/1672),round(42*h/941)
    x0=max(0,cx-pw);x1=min(w,cx+pw)
    y0=max(0,cy-ph);y1=min(h,cy+ph)
    patch=output[y0:y1,x0:x1].copy()
    hh,ww=patch.shape[:2]
    mx,my=cx-x0,cy-y0
    yy,xx=np.mgrid[:hh,:ww].astype("float32")
    falloff=np.exp(-((xx-mx)/(pw*.8))**4-((yy-my)/(ph*.52))**4)
    offset=np.clip((yy-my+4)/10,0,1)*falloff*float(amount)*round(11*h/941)
    moved=cv2.remap(patch,xx,(yy-offset).astype("float32"),cv2.INTER_LINEAR,
                    borderMode=cv2.BORDER_REFLECT)
    if amount>.16:
        opacity=min(.7,max(0,(float(amount)-.14)*.58))
        radius_x=max(1,round(24*w/1672*(.8+.2*amount)))
        radius_y=max(1,round(10*h/941*amount))
        mask=np.zeros((hh,ww),np.uint8)
        cv2.ellipse(mask,(mx,my+max(1,radius_y//2)),(radius_x,radius_y),
                    0,0,360,round(opacity*255),-1,cv2.LINE_AA)
        moved=(moved.astype("float32")*(1-mask[...,None]/255)+
               np.array([18,21,45],dtype="float32")*(mask[...,None]/255)).astype("uint8")
    fx=np.minimum(np.arange(ww)/max(1,ww*.12),(ww-1-np.arange(ww))/max(1,ww*.12))
    fy=np.minimum(np.arange(hh)/max(1,hh*.24),(hh-1-np.arange(hh))/max(1,hh*.24))
    alpha=np.clip(np.minimum(fy[:,None],fx[None,:]),0,1).astype("float32")
    output[y0:y1,x0:x1]=(patch*(1-alpha[...,None])+moved*alpha[...,None]).astype("uint8")
    zoom=1+.008*math.sin(n/(fps*6.5))
    if zoom>1.001:
        nw=int(w/zoom);nh=int(h/zoom);x=(w-nw)//2;y=(h-nh)//2
        output=cv2.resize(output[y:y+nh,x:x+nw],(w,h))
    if add_title:
        overlay=output.copy()
        cv2.rectangle(overlay,(0,h-85),(w,h),(10,20,30),-1)
        output=cv2.addWeighted(overlay,.46,output,.54,0)
        cv2.putText(output,"PEACE IS NOT A MIRACLE WE WAIT FOR",(26,h-47),
                    cv2.FONT_HERSHEY_SIMPLEX,.72,(239,243,248),2,cv2.LINE_AA)
        cv2.putText(output,"AN ADDRESS ON PEACE, JUSTICE & RESPONSIBILITY",(27,h-22),
                    cv2.FONT_HERSHEY_SIMPLEX,.36,(191,222,230),1,cv2.LINE_AA)
    return output

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--portrait",required=True)
    ap.add_argument("--movie",required=True)
    ap.add_argument("--voice",default="",help="Optional isolated narration for jaw driving")
    ap.add_argument("--output",required=True)
    ap.add_argument("--seconds",type=float,default=20)
    ap.add_argument("--fps",type=int,default=12)
    ap.add_argument("--width",type=int,default=960)
    ap.add_argument("--height",type=int,default=540)
    a=ap.parse_args()
    if not 1<=a.seconds<=3600:raise ValueError("duration must be 1..3600 seconds")
    if not 6<=a.fps<=30:raise ValueError("fps must be 6..30")
    if a.width<320 or a.height<180:raise ValueError("resolution too small")
    output=Path(a.output)
    output.parent.mkdir(parents=True,exist_ok=True)
    drive=a.voice or a.movie
    energy=envelope(drive,a.seconds,a.fps)
    still=portrait(a.portrait,(a.width,a.height))
    cmd=["ffmpeg","-nostdin","-loglevel","error","-y",
         "-f","rawvideo","-pixel_format","bgr24",
         "-video_size",f"{a.width}x{a.height}","-framerate",str(a.fps),
         "-i","pipe:0","-i",str(a.movie),"-t",str(a.seconds),
         "-map","0:v","-map","1:a:0","-c:v","libx264","-preset","veryfast",
         "-crf","25","-pix_fmt","yuv420p","-c:a","aac","-b:a","128k",
         "-movflags","+faststart",str(output)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    try:
        for i,amplitude in enumerate(energy):
            proc.stdin.write(frame(still,float(amplitude),i,a.fps).tobytes())
    finally:
        proc.stdin.close()
    if proc.wait():raise RuntimeError("video encoder failed")
    ff=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration,size",
                       "-of","json",str(output)],capture_output=True,text=True,check=True)
    metadata={
        "protocol":"HSI-EXPERIMENTAL-SPEAKER/0.1",
        "speaker_identity":"original synthetic character (not a public official)",
        "human_camera_recording":False,
        "phoneme_or_viseme_alignment_verified":False,
        "motion_method":"audio-energy-driven 2D mouth warp and modest camera zoom",
        "not_actual_political_event":True,
        "source_video_sha256":sha(a.movie),"portrait_sha256":sha(a.portrait),
        "drive_audio_sha256":sha(drive),"result_sha256":sha(output),
        "frames":len(energy),"fps":a.fps,"probe":json.loads(ff.stdout)}
    output.with_suffix(".provenance.json").write_text(
        json.dumps(metadata,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"SYNTHETIC_SPEAKER_PREVIEW","video":str(output),
                      "probe":metadata["probe"]},ensure_ascii=False))
if __name__=="__main__":main()
