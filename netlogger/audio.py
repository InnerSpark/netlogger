"""Receive AllStar audio over USRP and transcribe each transmission. Receive-only."""
import queue
import time
import socket
import struct
from pathlib import Path

import numpy as np

from . import config
from .netlog import log_text

USRP_HDR = struct.Struct(">4sIIIIIII")  # eye, seq, memory, keyup, talkgroup, type, mpxid, reserved
PROMPT_BASE = "Ham radio net check-ins with callsigns in phonetics, like Kilo Five Alpha Bravo Charlie."
# Stock phrases Whisper invents for silence and noise (it learned them from video captions)
HALLUCINATIONS = ("thanks for watching", "thank you for watching", "new videos every week", "subscribe",
                  "like and subscribe", "see you next time", "see you in the next video", "subtitles by",
                  "transcribed by", "pfft")
# Words that only show up if Whisper is parroting the prompt back
ECHO_WORDS = {"regulars", "phonetics", "callsigns", "ham", "like"}


def prompt():
    """Nudge Whisper toward ham radio talk and the calls this net usually hears."""
    from .netlog import known_calls
    calls = known_calls(limit=25)
    return PROMPT_BASE + (" Regulars: " + ", ".join(calls) + "." if calls else "")


def keep_text(segments, prompt_text):
    """Join Whisper segments, dropping the ones that aren't real speech.

    On noise, tones or CW IDs Whisper tends to invent text or repeat its prompt.
    Skip segments it marks as probably silent, low-confidence or looping, then
    drop the whole thing if what's left is just the prompt read back.
    """
    import re
    kept = []
    for seg in segments:
        if seg.no_speech_prob > 0.6 and seg.avg_logprob < -0.5:
            continue  # probably not speech
        if seg.avg_logprob < -1.2 or seg.compression_ratio > 2.4:
            continue  # low confidence, or stuck repeating itself
        kept.append(seg.text.strip())
    # cut stock phrases out rather than dropping the segment, in case a real call shares it
    for h in HALLUCINATIONS:
        kept = [re.sub(re.escape(h) + r"[\s!.,]*", "", t, flags=re.I).strip() for t in kept]
    text = " ".join(kept).strip()
    words = re.findall(r"[a-z0-9]+", text.lower())
    if not words:
        return ""
    prompt_words = set(re.findall(r"[a-z0-9]+", prompt_text.lower()))
    echoed = sum(w in ECHO_WORDS for w in words)
    if echoed >= 2 or (echoed and all(w in prompt_words for w in words)):
        return ""
    # the same short sentence over and over ("Niner. Stations. Niner.")
    sentences = [x.strip().lower() for x in re.split(r"[.!?]+", text) if x.strip()]
    if len(sentences) >= 3 and len(set(sentences)) <= len(sentences) // 2:
        return ""
    return text


def clean(pcm8k):
    """Radio audio is often quiet and rumbly. Remove DC and low rumble, then level it."""
    x = pcm8k.astype(np.float32) / 32768.0
    x = x - x.mean()
    # 1st-order high-pass around 200 Hz
    a = np.exp(-2 * np.pi * 200 / 8000)
    y = np.empty_like(x)
    prev_x = prev_y = 0.0
    for i, v in enumerate(x):
        prev_y = a * (prev_y + v - prev_x)
        prev_x = v
        y[i] = prev_y
    # Level to about -20 dBFS RMS, never clipping
    rms = float(np.sqrt(np.mean(y ** 2))) or 1e-9
    gain = min(0.1 / rms, 0.95 / (float(np.abs(y).max()) or 1e-9), 20.0)
    return y * gain


def save_clip(pcm8k):
    """Keep the last SAVE_AUDIO transmissions as WAV files for tuning."""
    import wave
    d = config.DATA_DIR / "audio"
    d.mkdir(parents=True, exist_ok=True)
    path = d / time.strftime("%Y%m%d-%H%M%S.wav")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(pcm8k.astype("<i2").tobytes())
    for old in sorted(d.glob("*.wav"))[:-config.SAVE_AUDIO]:
        old.unlink(missing_ok=True)
    return path

jobs = queue.Queue()

# For the Setup page
status = {"transcriber": "starting", "last_packet": None, "error": None}


def transcriber():
    if config.FAKE_TRANSCRIPTS:
        lines = iter(Path(config.FAKE_TRANSCRIPTS).read_text().splitlines())
        transcribe = lambda audio: next(lines, "")
        print("transcriber ready (fake)", flush=True)
        status["transcriber"] = "ready"
    else:
        from faster_whisper import WhisperModel
        status["transcriber"] = "loading"
        model = WhisperModel(config.WHISPER_MODEL, device="cpu", compute_type="int8", cpu_threads=config.WHISPER_THREADS,
                             download_root=str(config.DATA_DIR / "models"))

        def transcribe(audio):
            p = prompt()
            segs, _ = model.transcribe(
                audio, language="en", initial_prompt=p, beam_size=5, condition_on_previous_text=False,
                # skip tones, static and CW IDs before Whisper can invent words for them
                vad_filter=True, vad_parameters={"min_silence_duration_ms": 500, "speech_pad_ms": 200})
            return keep_text(list(segs), p)
        print(f"transcriber ready ({config.WHISPER_MODEL})", flush=True)
        status["transcriber"] = "ready"

    while True:
        pcm8k = jobs.get()
        seconds = len(pcm8k) / 8000
        if config.SAVE_AUDIO:
            try:
                save_clip(pcm8k)
            except OSError as e:
                print("couldn't save audio clip:", e, flush=True)
        x = clean(pcm8k)
        audio16 = np.interp(np.arange(0, len(x), 0.5), np.arange(len(x)), x).astype(np.float32)  # 8k -> 16k
        try:
            text = transcribe(audio16).strip()
        except Exception as e:
            print("transcribe error:", e, flush=True)
            continue
        if text:
            print(f"[{seconds:.1f}s] {text}", flush=True)
            log_text(text, seconds)


def listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", config.USRP_PORT))
    sock.settimeout(0.5)
    print(f"listening for USRP audio on udp/{config.USRP_PORT}", flush=True)
    buf = []

    def flush():
        if buf:
            pcm = np.frombuffer(b"".join(buf), dtype="<i2")
            if len(pcm) / 8000 >= config.MIN_SECONDS:  # skip kerchunks
                jobs.put(pcm.copy())
            buf.clear()

    while True:
        try:
            data = sock.recv(2048)
        except socket.timeout:
            flush()  # link dropped mid-transmission
            continue
        if len(data) < USRP_HDR.size or data[:4] != b"USRP":
            continue
        status["last_packet"] = time.time()
        _, _, _, keyup, _, ptype, _, _ = USRP_HDR.unpack_from(data)
        if ptype != 0:  # voice only
            continue
        if keyup:
            buf.append(data[USRP_HDR.size:])
        else:
            flush()  # unkey = end of transmission
