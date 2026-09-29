"""Replay a recording into the logger as if it came from AllStar.

Usage: python3 tools/replay.py net.wav [host] [port]
Splits the file into transmissions at gaps of silence, sends each as USRP
keyup packets followed by an unkey packet. Needs ffmpeg for non-8k-mono files.
"""
import socket
import struct
import subprocess
import sys
import time

import numpy as np

HDR = struct.Struct(">4sIIIIIII")
FRAME = 160  # 20 ms at 8 kHz


def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "8000",
                          "-f", "s16le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype="<i2")


def split(pcm, gap_s=0.8, thresh=500):
    """Yield chunks of audio separated by at least gap_s of quiet."""
    frames = [pcm[i:i + FRAME] for i in range(0, len(pcm), FRAME)]
    loud = [np.abs(f).max() > thresh if len(f) else False for f in frames]
    gap = int(gap_s / 0.02)
    out, cur, quiet = [], [], 0
    for f, l in zip(frames, loud):
        if l:
            cur.append(f); quiet = 0
        elif cur:
            cur.append(f); quiet += 1
            if quiet >= gap:
                out.append(cur[:-quiet]); cur, quiet = [], 0
    if cur:
        out.append(cur)
    return out


def main():
    path = sys.argv[1]
    host = sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1"
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 34001
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    seq = 0
    tx = split(load(path))
    print(f"{len(tx)} transmissions")
    for n, frames in enumerate(tx, 1):
        for f in frames:
            f = np.pad(f, (0, FRAME - len(f)))
            sock.sendto(HDR.pack(b"USRP", seq, 0, 1, 0, 0, 0, 0) + f.astype("<i2").tobytes(), (host, port))
            seq += 1
            time.sleep(0.02)
        sock.sendto(HDR.pack(b"USRP", seq, 0, 0, 0, 0, 0, 0) + bytes(FRAME * 2), (host, port))
        seq += 1
        print(f"  sent {n}: {len(frames) * 0.02:.1f}s")
        time.sleep(1.0)


if __name__ == "__main__":
    main()
