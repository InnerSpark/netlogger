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
PROMPT = ("Amateur radio net check-ins. Callsigns spoken in phonetics: "
          "Kilo Five Alpha Bravo Charlie, Whiskey, November, X-ray, Yankee, Zulu, niner.")

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
            segs, _ = model.transcribe(audio, language="en", initial_prompt=PROMPT, beam_size=5)
            return " ".join(s.text.strip() for s in segs)
        print(f"transcriber ready ({config.WHISPER_MODEL})", flush=True)
        status["transcriber"] = "ready"

    while True:
        pcm8k = jobs.get()
        seconds = len(pcm8k) / 8000
        x = pcm8k.astype(np.float32) / 32768.0
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
