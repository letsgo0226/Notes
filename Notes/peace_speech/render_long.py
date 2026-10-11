#!/usr/bin/env python3
"""HSI-inspired finite correspondence renderer for a long, English civic address.

Input: English text, audio policy, semantic editorial mappings, source file hashes.
Output: MP4, audio, music, captions, scene+frame correspondence and a verification
manifest. This is NOT a photorealistic lip-sync model or evidence of world peace.
"""
from __future__ import annotations
import argparse
import asyncio
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import time
import wave

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
FPS = 12
W, H = 960, 540
RATE = 16000

# Explicit editorial semantics, not a mathematical inference from moral language.
POLICY = [
    ("transparent_argument", "open civic reasoning", "measured", "minor"),
    ("sovereignty", "territorial integrity and international law", "solemn", "minor"),
    ("reliable_ceasefire", "security beyond temporary silence", "solemn", "minor"),
    ("human_dignity", "equal protection of human life", "warm", "major"),
    ("accountability", "justice and durable security", "steady", "minor"),
    ("ceasefire_verification", "independent monitoring", "focused", "minor"),
    ("humanitarian_protection", "civilian protection and safe access", "warm", "minor"),
    ("reconstruction", "transparent reconstruction", "resolved", "major"),
    ("security_guarantees", "testable post-agreement guarantees", "steady", "minor"),
    ("civic_participation", "protected dissent and participation", "warm", "major"),
    ("evidence_integrity", "verifiable claims and evidence", "focused", "minor"),
    ("care_and_reason", "compassion with accountable institutions", "warm", "major"),
    ("accountable_dialogue", "dialogue respecting sovereignty", "steady", "minor"),
    ("citizen_action", "nonviolent civic responsibility", "resolved", "major"),
    ("measurable_outcomes", "transparent indicators and feedback", "focused", "minor"),
    ("responsible_hope", "hope open to criticism", "warm", "major"),
    ("public_revision", "reasoned disagreement and revision", "warm", "major"),
    ("peace_as_responsibility", "lawful cooperation and continued scrutiny", "resolved", "major"),
]


def call(*cmd):
    subprocess.run([str(c) for c in cmd], check=True, stdout=subprocess.DEVNULL)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def serialize(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(2**20), b""):
            h.update(chunk)
    return h.hexdigest()


def duration(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def en_font():
    result = subprocess.run(["fc-match", "-f", "%{file}", "DejaVu Sans"],
                            capture_output=True, text=True, check=True)
    font = result.stdout.strip()
    if not font or not Path(font).exists():
        raise RuntimeError("DejaVu Sans font unavailable")
    return font


def lines(draw, text, font, width):
    out, cur = [], ""
    for word in text.split():
        candidate = (cur + " " + word).strip()
        if cur and draw.textbbox((0, 0), candidate, font=font)[2] > width:
            out.append(cur)
            cur = word
        else:
            cur = candidate
    if cur:
        out.append(cur)
    return out


def visual(scene, seq, count, mood, portrait, path):
    canvas = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(canvas)
    for y in range(H):
        t = y / H
        color = (int(14 + t * 8), int(25 + t * 15), int(43 + t * 18))
        draw.line((0, y, W, y), fill=color)
    # Optional original SPEAKER PORTRAIT is a still, never claim lip synchronization.
    # No licensed or scraped political identity is ever fetched automatically.
    if portrait:
        with Image.open(portrait) as source:
            person = source.convert("RGB")
            pw, ph = person.size
            crop_width = int(ph * 0.98)
            left = max(0, (pw - crop_width)//2)
            person = person.crop((left, 0, min(pw, left+crop_width), ph))
            person = person.resize((438, H), Image.Resampling.LANCZOS)
            canvas.paste(person, (0, 0))
            fade = Image.new("L", (438, H), 0)
            for x in range(438):
                v = int(235 * (min(1.0, x / 200.0) ** 2))
                ImageDraw.Draw(fade).line((x, 0, x, H), fill=v)
            overlay = Image.new("RGB", (438, H), (16, 31, 47))
            canvas.paste(overlay, (0, 0), fade)
    d = ImageDraw.Draw(canvas)
    title_font = ImageFont.truetype(en_font(), 37)
    label_font = ImageFont.truetype(en_font(), 20)
    small_font = ImageFont.truetype(en_font(), 17)
    x0 = 485 if portrait else 72
    maxwidth = W - x0 - 57
    d.line((x0, 98, x0+62, 98), fill=(134, 222, 206), width=4)
    d.text((x0, 115), "PEACE · JUSTICE · SHARED RESPONSIBILITY", fill=(150, 213, 203), font=small_font)
    y = 195
    for s in lines(d, scene["heading"], title_font, maxwidth):
        d.text((x0, y), s, fill=(246, 249, 250), font=title_font)
        y += 54
    y = max(y + 22, 315)
    for s in lines(d, scene["body"], label_font, maxwidth):
        d.text((x0, y), s, fill=(196, 219, 226), font=label_font)
        y += 32
    d.line((x0, 478, 903, 478), fill=(77, 118, 134), width=2)
    d.text((x0, 491), f"AN ADDRESS FOR PEACE   /   {mood.upper()}", fill=(154, 189, 201), font=small_font)
    d.text((857, 491), f"{seq:02}/{count:02}", fill=(154, 189, 201), font=small_font)
    canvas.save(path, optimize=True)


async def edge_speech(text, path, voice, rate):
    import edge_tts
    await edge_tts.Communicate(text, voice=voice, rate=rate).save(str(path))


def speech(text, output, engine, voice, rate):
    if engine == "edge":
        for retry in range(3):
            try:
                asyncio.run(edge_speech(text, output, voice, rate))
                if output.stat().st_size < 1000:
                    raise ValueError("Synthesized audio was empty")
                return
            except Exception:
                if retry == 2:
                    raise
                time.sleep(2**retry)
    else:
        call("espeak", "-v", "en-us", "-s", "121", "-w", output, text)


def music_file(out, seconds, scene_index, tone, mood):
    scale = (0, 3, 7) if tone == "minor" else (0, 4, 7)
    low = 45 + ((scene_index * 5) % 9)
    notes = [low, low+scale[1], low+scale[2], low+12]
    freqs = [440.0 * (2**((m-69)/12)) for m in notes]
    level = {"solemn": 0.07, "focused":0.06, "steady":0.08,
             "warm":0.09, "resolved":0.105, "measured":0.06}[mood]
    n = int(seconds * RATE)
    with wave.open(str(out), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(RATE)
        step = 2048
        for start in range(0, n, step):
            buf = bytearray()
            for i in range(start, min(start+step, n)):
                t = i/RATE
                envelope = min(1, t/1.5, max(0, (seconds-t)/1.5))
                slow = 0.83 + 0.17*math.sin(2*math.pi*0.075*t)
                tone_value = sum(math.sin(2*math.pi*f*t) / (1+j) for j,f in enumerate(freqs))
                sample = int(max(-32767, min(32767, 32767*level*envelope*slow*tone_value)))
                buf.extend(struct.pack("<h", sample))
            wf.writeframesraw(buf)
    return {"mode": tone, "mood": mood, "midi": notes,
            "gain_nominal": level, "synthesis": "original deterministic DSP"}


def stamp(t):
    ms = int(round(t*1000))
    return f"{ms//3600000:02}:{(ms//60000)%60:02}:{(ms//1000)%60:02},{ms%1000:03}"


def subtitle_chunks(txt, t0, seconds):
    # Approximate timing, intentionally NOT described as forced alignment.
    words = txt.split()
    segments = [words[i:i+11] for i in range(0, len(words), 11)]
    out = []
    count = len(words)
    offset = 0
    for group in segments:
        start = t0 + max(0, seconds-0.4) * offset/count
        offset += len(group)
        end = t0 + max(0, seconds-0.4) * offset/count
        out.append((start, end, " ".join(group)))
    return out


def notes_inventory():
    root = REPO/"Notes"
    return [
        {"source": str(p.relative_to(REPO)), "sha256": file_sha(p)}
        for p in sorted(root.rglob("*"))
        if p.is_file() and "peace_speech" not in p.parts and "__pycache__" not in p.parts
    ]


def make(args):
    for executable in ("ffmpeg", "ffprobe", "fc-match"):
        if not shutil.which(executable):
            raise RuntimeError(f"Missing {executable}")
    if args.engine == "espeak" and not shutil.which("espeak"):
        raise RuntimeError("Missing espeak")
    data_path = Path(args.script).resolve()
    data = json.loads(data_path.read_text(encoding="utf-8"))
    entries = data["scenes"]
    if args.limit_scenes:
        entries = entries[:args.limit_scenes]
    if not entries:
        raise ValueError("No scenes")
    if len(entries) > len(POLICY):
        raise ValueError("No editorial correspondence rule for an added scene")
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    temp = out/"segments"
    temp.mkdir(exist_ok=True)
    still = Path(args.speaker_image).resolve() if args.speaker_image else None
    if still and not still.is_file():
        raise FileNotFoundError(still)
    all_segments, scenes, captions, music_records, transcript = [], [], [], [], []
    audio_segments = []
    t = 0.0
    for i, entry in enumerate(entries):
        goal, policy, mood, tone = POLICY[i]
        framepath = temp/f"frame_{i:02}.png"
        audiopath = temp/f"speech_{i:02}.{'mp3' if args.engine=='edge' else 'wav'}"
        scorepath = temp/f"music_{i:02}.wav"
        segmentpath = temp/f"scene_{i:02}.mp4"
        visual(entry, i+1, len(entries), mood, still, framepath)
        speech(entry["english"], audiopath, args.engine, args.voice, args.rate)
        sec = duration(audiopath)+0.65
        music = music_file(scorepath, sec, i, tone, mood)
        call("ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
             "-loop", "1", "-framerate", str(FPS), "-i", framepath,
             "-i", audiopath, "-i", scorepath,
             "-filter_complex",
             "[1:a]aformat=sample_rates=44100:channel_layouts=stereo,apad[a];"
             "[2:a]aformat=sample_rates=44100:channel_layouts=stereo,volume=0.62[b];"
             "[a][b]amix=inputs=2:duration=longest:dropout_transition=0[m]",
             "-map", "0:v", "-map", "[m]", "-t", f"{sec:.3f}",
             "-c:v", "libx264", "-preset", "ultrafast", "-crf", str(args.crf),
             "-pix_fmt", "yuv420p", "-r", str(FPS),
             "-c:a", "aac", "-b:a", "112k", "-ar", "44100",
             "-movflags", "+faststart", segmentpath)
        scenes.append({
            "scene":i+1, "input_sha256":digest(serialize(entry)),
            "start_seconds":round(t,3), "duration_seconds":round(sec,3),
            "policy_goal_id":goal, "policy_proposal":policy,
            "music":music, "image_sha256":file_sha(framepath),
            "audio_sha256":file_sha(audiopath),
            "music_sha256":file_sha(scorepath),
            "render_sha256":file_sha(segmentpath),
            "lip_sync":{"status":"NOT_GENERATED", "reason":"requires a separately validated performance/lip-sync renderer"}
        })
        music_records.append({"scene":i+1, **music})
        for a,b,line in subtitle_chunks(entry["english"], t, sec):
            captions.append((a,b,line))
        transcript += [f"## {i+1:02}. {entry['heading']}", "", entry["english"], ""]
        t+=sec
        audio_segments.append(audiopath)
        all_segments.append(segmentpath)
        print(f"rendered {i+1}/{len(entries)}: {sec:.2f}s / total {t:.1f}s", flush=True)
    # Duration assurance is checked against the actual combined video, never simulated.
    paths = temp/"concat.txt"
    paths.write_text("".join("file '"+p.name+"'\n" for p in all_segments), encoding="utf-8")
    movie=out/"peace_address_english.mp4"
    call("ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
         "-f", "concat", "-safe", "0", "-i", paths, "-c", "copy", movie)
    actual=duration(movie)
    if not args.limit_scenes and actual < args.min_seconds:
        raise ValueError(f"Film too short: {actual:.2f}s < {args.min_seconds}s")
    srt=out/"captions.en.srt"
    srt.write_text("\n".join(f"{j+1}\n{stamp(a)} --> {stamp(b)}\n{text}\n"
                             for j,(a,b,text) in enumerate(captions)), encoding="utf-8")
    transcript_path=out/"transcript.en.md"
    transcript_path.write_text("# Peace Is Not a Miracle We Wait For\n\n" +
        "\n".join(transcript) +
        "\n\n## Research references (not official endorsement)\n" +
        "\n".join("- "+s for s in data.get("sources", []))+
        "\n\nProduction notice: this is an original synthetic production, not a recording of a real political event.\n",
        encoding="utf-8")
    # The separate English voice track contains no background music.
    tracklist=temp/"narration_concat.txt"
    tracklist.write_text("".join("file '"+p.name+"'\n" for p in audio_segments),encoding="utf-8")
    call("ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
         "-f", "concat", "-safe", "0", "-i", tracklist,
         "-c:a", "libmp3lame", "-q:a", "4", out/"voiceover.en.mp3")
    video_frames=round(actual*FPS)
    mapping=out/"frame_correspondence.jsonl"
    with mapping.open("w",encoding="utf-8") as fw:
        scene_pos=0
        for frame_idx in range(video_frames):
            at=frame_idx/FPS
            while scene_pos+1<len(scenes) and at >= scenes[scene_pos]["start_seconds"]+scenes[scene_pos]["duration_seconds"]:
                scene_pos+=1
            sc=scenes[scene_pos]
            state={"frame":frame_idx,"time_seconds":round(at,6),"scene":sc["scene"],
                   "policy_goal_id":sc["policy_goal_id"],
                   "image_sha256":sc["image_sha256"],
                   "music_midi":sc["music"]["midi"],
                   "lip_sync_rendered":False}
            fw.write(json.dumps(state,separators=(",",":"))+"\n")
    metadata={
        "protocol":"HSI-PEACE-AV-CORRESPONDENCE/1.0",
        "production":"ORIGINAL_SYNTHETIC_SPEECH",
        "not_official_footage":True,
        "not_a_real_political_event":True,
        "language":"English",
        "narration":{"engine":args.engine,"voice":args.voice if args.engine=="edge" else "espeak en-us"},
        "picture":{"type":"ORIGINAL_STATIC_ILLUSTRATED_SCENES_WITH_OPTIONAL_STILL_SPEAKER",
                   "speaker_still":bool(still),"natural_lip_sync":False},
        "music":{"type":"RULE_BASED_DSP", "semantic_correspondence":"DECLARED_EDITORIAL_RULES_NOT_CAUSAL_PROOF"},
        "peace_goal_validation":"NOT_EVIDENCE_OF_REAL_WORLD_PEACE",
        "note":"Scene-to-goal association is normative/editorial; numerical matching cannot prove peace or persuasion.",
        "video_duration_seconds":round(actual,3),
        "video_frames_estimated":video_frames,
        "target_seconds":args.min_seconds,
        "original_script_sha256":file_sha(data_path),
        "notes_source_inventory":notes_inventory(),
        "scenes":scenes,
        "sources":data.get("sources",[])
    }
    (out/"correspondence.json").write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (out/"SHA256SUMS").write_text(
        "".join(file_sha(p)+"  "+p.name+"\n" for p in sorted(out.iterdir())
                if p.is_file() and p.name!="SHA256SUMS"),encoding="utf-8")
    print("DONE", movie, "duration", actual, "scenes", len(scenes),flush=True)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--script",default=str(HERE/"long_speech.en.json"))
    ap.add_argument("--output",default="影音/latest")
    ap.add_argument("--engine",choices=["edge","espeak"],default="edge")
    ap.add_argument("--voice",default="en-US-AndrewNeural")
    ap.add_argument("--rate",default="-13%")
    ap.add_argument("--speaker-image",default="")
    ap.add_argument("--crf",type=int,default=29)
    ap.add_argument("--min-seconds",type=int,default=600)
    ap.add_argument("--limit-scenes",type=int,default=0)
    args=ap.parse_args()
    make(args)


if __name__=="__main__":
    main()
