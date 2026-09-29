"""Turn a transcript into US callsigns and check-in flags."""
import re

PHONETIC = {
    "alpha": "A", "alfa": "A", "bravo": "B", "charlie": "C", "delta": "D",
    "echo": "E", "foxtrot": "F", "fox": "F", "golf": "G", "hotel": "H",
    "india": "I", "juliet": "J", "juliett": "J", "kilo": "K", "lima": "L",
    "mike": "M", "november": "N", "oscar": "O", "papa": "P", "quebec": "Q",
    "romeo": "R", "sierra": "S", "tango": "T", "uniform": "U", "victor": "V",
    "whiskey": "W", "whisky": "W", "xray": "X", "yankee": "Y", "zulu": "Z",
}
DIGITS = {
    "zero": "0", "oh": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9", "niner": "9",
}
# US amateur callsign: 1x2, 1x3, 2x1, 2x2, 2x3 formats
CALL_RE = re.compile(r"^(?:[KNW][A-Z]?|A[A-L])[0-9][A-Z]{1,3}$")

FLAG_PATTERNS = {
    "traffic": re.compile(r"\bwith (?:some )?traffic\b|\bhave traffic\b|\bgot traffic\b"),
    "short_time": re.compile(r"\bshort time\b"),
    "recheck": re.compile(r"\brecheck\b|\bcall (?:me )?back\b|\bcome back to me\b|\bcheck back\b"),
}


def _tokens(text):
    t = text.lower().replace("x-ray", "xray").replace("x ray", "xray")
    # punctuation stays as a token so "K5AB, Mike" doesn't become K5ABM
    return re.findall(r"[a-z0-9]+|[,.;:!?]", t)


def _chars(tok):
    """Map one token to callsign characters, or None if it can't be part of one."""
    if tok in PHONETIC:
        return PHONETIC[tok]
    if tok in DIGITS:
        return DIGITS[tok]
    if re.fullmatch(r"[a-z]|[0-9]+", tok):
        return tok.upper()
    # Whisper often writes the call itself, like "k5abc"
    if re.fullmatch(r"[a-z]{1,2}[0-9][a-z]{1,3}", tok):
        return tok.upper()
    return None


def extract_calls(text):
    """Return callsigns in order of appearance, no duplicates."""
    runs, cur = [], ""
    for tok in _tokens(text):
        c = _chars(tok)
        if c is None:
            if cur:
                runs.append(cur)
            cur = ""
        else:
            cur += c
    if cur:
        runs.append(cur)

    found = []
    for run in runs:
        i = 0
        while i < len(run):
            match = None
            for end in range(min(len(run), i + 6), i + 2, -1):  # longest first
                if CALL_RE.match(run[i:end]):
                    match = run[i:end]
                    break
            if match:
                if match not in found:
                    found.append(match)
                i += len(match)
            else:
                i += 1
    return found


def extract_flags(text):
    t = text.lower()
    return sorted(k for k, rx in FLAG_PATTERNS.items() if rx.search(t))
