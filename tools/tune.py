"""Compare Whisper models on saved transmissions (SAVE_AUDIO=N in the settings).

On an install.sh server:
  sudo -u netlogger env $(sudo cat /etc/netlogger/netlogger.env | xargs) \\
    /opt/netlogger/.venv/bin/python /opt/netlogger/tools/tune.py base.en small.en

Prints each clip's transcript and the calls found, per model, so you can pick the best one.
"""
import sys
import time
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from netlogger import config, db  # noqa: E402
from netlogger.audio import clean, prompt  # noqa: E402
from netlogger.netlog import calls_in  # noqa: E402


def load(path):
    with wave.open(str(path)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")


def main():
    models = sys.argv[1:] or [config.WHISPER_MODEL]
    clips = sorted((config.DATA_DIR / "audio").glob("*.wav"))
    if not clips:
        sys.exit(f"No clips in {config.DATA_DIR / 'audio'}. Set SAVE_AUDIO=50 and let it hear a few transmissions.")
    db.connect()
    from faster_whisper import WhisperModel
    print(f"prompt: {prompt()}\n")
    for name in models:
        model = WhisperModel(name, device="cpu", compute_type="int8", cpu_threads=config.WHISPER_THREADS,
                             download_root=str(config.DATA_DIR / "models"))
        print(f"=== {name}")
        total = 0.0
        for clip in clips:
            x = clean(load(clip))
            audio = np.interp(np.arange(0, len(x), 0.5), np.arange(len(x)), x).astype(np.float32)
            t = time.time()
            segs, _ = model.transcribe(audio, language="en", initial_prompt=prompt(), beam_size=5,
                                       condition_on_previous_text=False)
            text = " ".join(s.text.strip() for s in segs)
            total += time.time() - t
            print(f"  {clip.name}  [{len(x) / 8000:.1f}s]  {text!r}  -> {calls_in(text) or '-'}")
        print(f"  took {total:.1f}s total\n")


if __name__ == "__main__":
    main()
