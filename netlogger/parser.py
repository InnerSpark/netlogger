"""Turn a transcript into amateur callsigns (any country) and check-in flags."""
import re

PHONETIC = {
    "alpha": "A", "alfa": "A", "bravo": "B", "charlie": "C", "charley": "C", "delta": "D",
    "echo": "E", "foxtrot": "F", "fox": "F", "golf": "G", "hotel": "H",
    "india": "I", "juliet": "J", "juliett": "J", "juliette": "J", "kilo": "K", "keelo": "K",
    "lima": "L", "mike": "M", "november": "N", "oscar": "O", "papa": "P", "quebec": "Q",
    "romeo": "R", "sierra": "S", "siera": "S", "tango": "T", "uniform": "U", "victor": "V",
    "whiskey": "W", "whisky": "W", "wiskey": "W", "xray": "X", "exray": "X", "yankee": "Y",
    "yanky": "Y", "zulu": "Z",
}
# Includes ITU radio pronunciations Whisper sometimes writes out ("fife", "tree", "niner")
DIGITS = {
    "zero": "0", "oh": "0", "one": "1", "two": "2", "three": "3", "tree": "3", "four": "4",
    "five": "5", "fife": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9", "niner": "9",
}
# ITU amateur callsign: prefix (1-2 letters, letter+digit or digit+letter), a digit,
# then a 1-3 letter suffix. W6UXD, VE3ABC, G4ABC, M0XYZ, 2E0ABC, DL1AB, VK2ABC, 9A1AA, E73ABC.
CALL_RE = re.compile(r"^(?:[A-Z]{1,2}|[A-Z][0-9]|[0-9][A-Z])[0-9][A-Z]{1,3}$")
US_RE = re.compile(r"^(?:[KNW][A-Z]?|A[A-L])[0-9][A-Z]{1,3}$")


def is_us(call):
    """US calls are the ones callook.info (the FCC database) can look up."""
    return bool(US_RE.match(call or ""))

FLAG_PATTERNS = {
    "traffic": re.compile(r"\bwith (?:some )?traffic\b|\bhave traffic\b|\bgot traffic\b"),
    "short_time": re.compile(r"\bshort time\b"),
    "recheck": re.compile(r"\brecheck\b|\bcall (?:me )?back\b|\bcome back to me\b|\bcheck back\b"),
}


def _tokens(text):
    t = text.lower().replace("\u2019", "'")
    t = re.sub(r"\b(?:x|ex)[- ]?ray\b", "xray", t)
    t = re.sub(r"(\w)'s\b", r"\1", t)  # "Six's X-ray" -> "six xray"
    t = re.sub(r"\b(\w+)'(m|re|ve|ll|d|t)\b", r"\1\2", t)  # "I'm" is a word, not the letters I and M
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
    if re.fullmatch(r"(?:[a-z]{1,2}|[a-z][0-9]|[0-9][a-z])[0-9][a-z]{1,3}", tok):
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
            for end in range(min(len(run), i + 7), i + 2, -1):  # longest first
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


PARTIAL_RE = re.compile(r"[A-Z0-9]{4,7}")


def partial_runs(text):
    """Callsign-like fragments that didn't make a full call, e.g. "6UXD" when the prefix was garbled."""
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
    return [r for r in runs if PARTIAL_RE.fullmatch(r) and any(ch.isdigit() for ch in r)]


def match_known(text, known):
    """If no full call was heard, see if a fragment points at exactly one call we've logged before."""
    hits = set()
    for frag in partial_runs(text):
        for call in known:
            if frag in call or call in frag:
                hits.add(call)
    return hits.pop() if len(hits) == 1 else None


def _subsequence(short, long):
    it = iter(long)
    return all(ch in it for ch in short)


def resolve(call, known):
    """Snap a clipped call to a call we've logged before, e.g. W6U or W6X -> W6UXD.
    Only when exactly one known call fits, and it shares the prefix and digit."""
    if not call or call in known:
        return call
    # One stray letter glued on the front ("Mike K5ABC" -> MK5ABC) of a call we know
    extra = [k for k in known if len(k) == len(call) - 1 and call.endswith(k)]
    if len(extra) == 1:
        return extra[0]
    m = re.match(r"[A-Z]+[0-9]", call)
    head = m.group(0) if m else call[:2]
    fits = [k for k in known if len(k) > len(call) and k.startswith(head) and _subsequence(call, k)]
    return fits[0] if len(fits) == 1 else call
