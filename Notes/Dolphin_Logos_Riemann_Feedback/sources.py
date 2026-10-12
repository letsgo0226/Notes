"""Public, bounded source intake. No video/audio download or transcript publication."""
import hashlib
import html
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request
import wave
import math
from array import array
import sys

CHANNEL = "UCLoHjca5L0KJ3i14MvhcroA"
CATALOG_LIMIT = 512
MAX_SOURCE_BYTES = 2_000_000


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def sha(value):
    return hashlib.sha256(value).hexdigest()


class QuietLogger:
    def debug(self, *args): pass
    def warning(self, *args): pass
    def error(self, *args): pass


def youtube_options():
    return {"quiet": True, "no_warnings": True, "logger": QuietLogger(),
            "socket_timeout": 15, "retries": 0, "extractor_retries": 0,
            "skip_download": True, "noplaylist": True}


def normalize_catalog(info):
    if info.get("channel_id") != CHANNEL:
        raise ValueError("Channel identity differs from the configured official channel")
    entries = {}
    raw_entries = list(info.get("entries") or [])
    for row in raw_entries[:CATALOG_LIMIT]:
        uid = row.get("id", "")
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", uid):
            continue
        if row.get("channel_id") and row["channel_id"] != CHANNEL:
            continue
        entries[uid] = {"id": uid, "channel_id": CHANNEL,
                        "title": str(row.get("title", ""))[:300],
                        "url": "https://www.youtube.com/watch?v=" + uid,
                        "duration_seconds": row.get("duration")}
    if not entries:
        raise ValueError("Official catalog returned no usable video records")
    return {"protocol": "DOLPHIN-SOURCE-CATALOG/1", "channel_id": CHANNEL,
            "status": "CATALOG_READ", "scan_limit": CATALOG_LIMIT,
            "possibly_truncated": len(raw_entries) >= CATALOG_LIMIT,
            "entries": sorted(entries.values(), key=lambda x: x["id"])}


def sync_catalog(config, previous=None):
    try:
        import yt_dlp
        options = youtube_options()
        options.update(extract_flat=True, playlistend=CATALOG_LIMIT, noplaylist=False)
        with yt_dlp.YoutubeDL(options) as ydl:
            catalog = normalize_catalog(ydl.extract_info(config["channel_url"], download=False))
        catalog["priority_ids"] = config.get("priority_ids", [])
        return catalog
    except Exception as exc:
        fallback = dict(previous or config["seed_catalog"])
        fallback["status"] = "CATALOG_REFRESH_UNAVAILABLE"
        fallback["error_type"] = type(exc).__name__
        return fallback


def caption_text(raw, extension):
    if len(raw) > MAX_SOURCE_BYTES:
        raise ValueError("Caption response exceeds intake bound")
    decoded = raw.decode("utf-8")
    if extension == "json3":
        obj = json.loads(decoded)
        pieces = ["".join(str(s.get("utf8", "")) for s in e.get("segs", []))
                  for e in obj.get("events", [])]
    else:
        pieces = []
        for line in decoded.splitlines():
            if (not line.strip() or "-->" in line or line.strip().isdigit()
                    or line.startswith(("WEBVTT", "Kind:", "Language:", "NOTE"))):
                continue
            pieces.append(re.sub(r"<[^>]+>", "", line))
    out = []
    for piece in pieces:
        text = html.unescape(piece).strip()
        if text and (not out or text != out[-1]):
            out.append(text)
    return " ".join(out)


def caption_url_allowed(url):
    p = urllib.parse.urlsplit(url)
    return (p.scheme == "https" and p.hostname in ("www.youtube.com", "youtube.com")
            and p.path == "/api/timedtext" and not p.username and not p.password)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Caption redirects are not accepted")


def select_caption(info):
    for kind, collection in (("PUBLISHED_CAPTION", info.get("subtitles") or {}),
                             ("AUTO_CAPTION", info.get("automatic_captions") or {})):
        languages = sorted(collection, key=lambda x: (not x.startswith("en"), x))
        for lang in languages:
            if not lang.startswith(("en", "zh")):
                continue
            formats = sorted(collection[lang], key=lambda x: x.get("ext") != "json3")
            for item in formats:
                if item.get("ext") in ("json3", "vtt", "srt") and caption_url_allowed(item.get("url", "")):
                    return kind, lang, item
    return None


def material_for(entry, offline=False):
    base = {"id": entry["id"], "title": entry["title"], "url": entry["url"],
            "channel_id": entry.get("channel_id"), "modality": "METADATA_ONLY",
            "read_status": "TITLE_ONLY", "text": entry["title"],
            "watched_video": False, "listened_audio": False}
    if offline:
        base["read_status"] = "OFFLINE_METADATA"
    else:
        try:
            import yt_dlp
            with yt_dlp.YoutubeDL(youtube_options()) as ydl:
                info = ydl.extract_info(entry["url"], download=False)
            if info.get("channel_id") != CHANNEL:
                raise ValueError("Video uploader identity mismatch")
            selected = select_caption(info)
            if selected:
                kind, lang, item = selected
                req = urllib.request.Request(item["url"], headers={"User-Agent": "Dolphin-Logos/1"})
                with urllib.request.build_opener(NoRedirect()).open(req, timeout=20) as response:
                    text = caption_text(response.read(MAX_SOURCE_BYTES + 1), item["ext"])
                if not text.strip():
                    raise ValueError("Empty captions")
                base.update(modality=kind, language=lang, text=text, read_status="CAPTION_READ")
            else:
                description = str(info.get("description") or "").strip()
                if description and len(description.encode("utf-8")) <= MAX_SOURCE_BYTES:
                    base.update(text=description, modality="VIDEO_DESCRIPTION",
                                read_status="DESCRIPTION_READ_NO_CAPTION")
                else:
                    base["read_status"] = "NO_PUBLIC_CAPTION"
        except Exception as exc:
            base.update(read_status="CAPTION_UNAVAILABLE", error_type=type(exc).__name__)
    base["text_sha256"] = sha(base["text"].encode("utf-8"))
    base["available_characters"] = len(base["text"])
    return base


def text_window(material, visit, width=2400):
    text = material["text"]
    start = (visit * width) % max(1, len(text))
    snippet = text[start:start + width]
    return {"start": start, "end": start + len(snippet), "text": snippet,
            "sha256": sha(snippet.encode("utf-8"))}


def audio_features(path):
    """Analyze a user-provided PCM WAV; never download or embed audio."""
    path = Path(path)
    if path.stat().st_size > 100_000_000:
        raise ValueError("WAV exceeds 100 MB intake bound")
    with wave.open(str(path), "rb") as audio:
        channels, width, rate, frames, compression, _ = audio.getparams()
        if width != 2 or compression != "NONE" or channels not in (1, 2) or rate <= 0:
            raise ValueError("Expected mono/stereo 16-bit PCM WAV")
        samples = array("h", audio.readframes(min(frames, rate * 60)))
    if sys.byteorder != "little":
        samples.byteswap()
    return {"modality": "LOCAL_AUDIO_FEATURES", "duration_seconds": frames / rate,
            "analyzed_seconds": min(frames, rate * 60) / rate,
            "channels": channels, "sample_rate": rate,
            "rms": math.sqrt(sum(x*x for x in samples) / max(1, len(samples))) / 32768,
            "peak": max((abs(x) for x in samples), default=0) / 32768,
            "listened_audio": False, "semantic_audio_understanding": False,
            "sha256": sha(path.read_bytes())}
