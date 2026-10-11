#!/usr/bin/env python3
"""Render an openly fictional, illustrated civic address. Offline, no credentials."""
import argparse
import asyncio
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import time

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
W, H = 960, 540
FPS = 15


def run(argv):
    subprocess.run(argv, check=True, stdout=subprocess.DEVNULL)


def font_file():
    out = subprocess.run(
        ["fc-match", "-f", "%{file}", "Noto Sans CJK TC"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    if not out or not Path(out).is_file():
        raise RuntimeError("Missing CJK font; install fonts-noto-cjk")
    return out


def wrap(draw, txt, font, width):
    result, buf = [], ""
    for ch in txt:
        if draw.textbbox((0, 0), buf + ch, font=font)[2] > width and buf:
            result.append(buf)
            buf = ch
        else:
            buf += ch
    if buf:
        result.append(buf)
    return result


def frame(scene, idx, fontpath, output):
    im = Image.new("RGB", (W, H))
    px = im.load()
    # Graphic art generated from geometry only, not journalistic footage.
    for y in range(H):
        for x in range(W):
            t = y / H
            glow = max(0, 1 - math.hypot((x - 745) / 550, (y - 280) / 410))
            px[x, y] = (int(11 + 8*t + 17*glow), int(27 + 11*t + 21*glow), int(43 + 16*t + 29*glow))
    d = ImageDraw.Draw(im)
    accent = (133, 216, 200)
    muted = (168, 193, 207)
    for j in range(5):
        k = 92 + 58*j
        d.ellipse((635-k, 267-k, 635+k, 267+k), outline=(48+j*8, 86+j*9, 104+j*8), width=1)
    for i in range(31):
        ax = 610 + int(260*math.sin(i*2.37))
        ay = 265 + int(205*math.cos(i*1.89))
        d.ellipse((ax-1, ay-1, ax+1, ay+1), fill=(112, 178, 176))
    d.line((74, 88, 142, 88), fill=accent, width=4)
    d.text((153, 73), scene["eyebrow"], font=ImageFont.truetype(fontpath, 21), fill=accent)
    d.text((74, 112), "CIVIC PEACE ADDRESS · 2026", font=ImageFont.truetype(fontpath, 17), fill=muted)
    headline = ImageFont.truetype(fontpath, 42)
    body = ImageFont.truetype(fontpath, 26)
    yy = 194
    for line in wrap(d, scene["heading"], headline, 790):
        d.text((74, yy), line, font=headline, fill=(245, 248, 247), stroke_width=0)
        yy += 62
    yy += 19
    for line in wrap(d, scene["body"], body, 782):
        d.text((76, yy), line, font=body, fill=(213, 228, 230))
        yy += 44
    d.line((74, 479, 885, 479), fill=(78, 119, 131), width=1)
    d.text((74, 493), "和平 · 正義 · 共同責任", font=ImageFont.truetype(fontpath, 17), fill=muted)
    d.text((839, 493), f"{idx+1:02}/10", font=ImageFont.truetype(fontpath, 17), fill=accent)
    im.save(output, optimize=True)


def srt_time(t):
    ms = round(t * 1000)
    return f"{ms//3600000:02}:{(ms//60000)%60:02}:{(ms//1000)%60:02},{ms%1000:03}"


def media_duration(media):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(media)],
        capture_output=True, text=True, check=True,
    )
    duration = float(result.stdout.strip())
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Invalid audio duration")
    return duration


def generate_narration(text, audio, args):
    if args.tts == "espeak":
        run(["espeak", "-v", "en-us", "-s", "132", "-p", "42", "-w", str(audio), text])
        return
    try:
        import edge_tts
    except ImportError as exc:
        raise RuntimeError("edge-tts missing; pip install edge-tts or choose --tts espeak") from exc
    for attempt in range(3):
        try:
            asyncio.run(edge_tts.Communicate(text, args.voice, rate=args.rate).save(str(audio)))
            if not audio.is_file() or audio.stat().st_size < 500:
                raise RuntimeError("Empty speech synthesis result")
            return
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="dist/peace_speech")
    parser.add_argument("--limit-scenes", type=int, default=0, help="For rendering smoke tests")
    parser.add_argument("--tts", choices=["edge", "espeak"], default="edge",
                        help="Microsoft Edge natural English speech (default), or offline eSpeak")
    parser.add_argument("--voice", default="en-US-AndrewNeural", help="Microsoft Edge English voice")
    parser.add_argument("--rate", default="-8%", help="Microsoft Edge speech rate (e.g. -8%%)")
    args = parser.parse_args()
    programs = ["ffmpeg", "ffprobe", "fc-match"] + (["espeak"] if args.tts == "espeak" else [])
    for name in programs:
        if not shutil.which(name):
            raise RuntimeError(f"Missing required program: {name}")
    data = json.loads((HERE / "speech.json").read_text(encoding="utf-8"))
    scenes = data["scenes"][:args.limit_scenes or None]
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    temp = out / "_segments"
    temp.mkdir(exist_ok=True)
    fonts = font_file()
    segment_paths = []
    captions = []
    english_captions = []
    voice_label = ("Microsoft Edge " + args.voice) if args.tts == "edge" else "offline eSpeak en-us"
    transcript = [f"# {data['title']}", "", f"原創演說影片。英語合成旁白：{voice_label}；繁體中文與英文字幕。", "", "製作資訊：本作品使用原創合成影像與合成語音，並非任何政府或國際組織的真實演說記錄。", ""]
    elapsed = 0
    for idx, s in enumerate(scenes):
        img = temp / f"frame_{idx:02}.png"
        audio = temp / f"narration_{idx:02}.{'mp3' if args.tts == 'edge' else 'wav'}"
        mp4 = temp / f"scene_{idx:02}.mp4"
        frame(s, idx, fonts, img)
        generate_narration(s["english"], audio, args)
        duration = media_duration(audio) + 0.55
        fadeout = max(0.0, duration - 0.65)
        run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-loop", "1", "-framerate", str(FPS), "-i", str(img), "-i", str(audio), "-t", f"{duration:.3f}", "-vf", f"fade=t=in:st=0:d=0.45,fade=t=out:st={fadeout:.3f}:d=0.6", "-af", "apad", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "27", "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "112k", "-ar", "44100", str(mp4)])
        segment_paths.append(mp4)
        captions.append(f"{idx+1}\n{srt_time(elapsed)} --> {srt_time(elapsed+duration)}\n{s['heading']}\n{s['body']}\n")
        english_captions.append(f"{idx+1}\n{srt_time(elapsed)} --> {srt_time(elapsed+duration)}\n{s['english']}\n")
        transcript += [f"## {idx+1:02} · {s['heading']}", "", s["body"], "", f"English narration: {s['english']}", ""]
        elapsed += duration
        print(f"scene {idx+1}/{len(scenes)}: {duration:.1f}s", flush=True)
    listfile = temp / "concat.txt"
    listfile.write_text("".join(f"file '{p.name}'\n" for p in segment_paths), encoding="utf-8")
    run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listfile), "-c", "copy", str(out / "peace_speech.mp4")])
    (out / "captions.zh-TW.srt").write_text("\n".join(captions), encoding="utf-8")
    (out / "captions.en.srt").write_text("\n".join(english_captions), encoding="utf-8")
    run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i",
         str(out / "peace_speech.mp4"), "-vn", "-c:a", "libmp3lame",
         "-q:a", "3", str(out / "voiceover.en.mp3")])
    transcript += ["## Sources / 參考資料", "", "以下連結用於核對背景，並非對本作品的官方背書。", ""]
    transcript += [f"- {url}" for url in data["sources"]]
    (out / "transcript.md").write_text("\n".join(transcript) + "\n", encoding="utf-8")
    meta = {"protocol": "FICTIONAL-PEACE-ADDRESS/1.0", "date": data["date"], "fictional": True, "official_statement": False, "scenes": len(scenes), "duration_estimate_seconds": round(elapsed, 2), "speech_source_sha256": hashlib.sha256((HERE / "speech.json").read_bytes()).hexdigest(), "sources": data["sources"], "narration": voice_label, "tts_provider": ("Microsoft Edge online speech (community edge-tts integration; not Azure Speech)" if args.tts == "edge" else "offline eSpeak"), "artwork": "original deterministic geometric illustration", "depiction": "original synthetic production, not an actual event recording"}
    (out / "provenance.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / "SHA256SUMS").write_text("".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in sorted(out.iterdir()) if p.is_file() and p.name != "SHA256SUMS"), encoding="utf-8")
    print("render complete:", out / "peace_speech.mp4", flush=True)


if __name__ == "__main__":
    main()
