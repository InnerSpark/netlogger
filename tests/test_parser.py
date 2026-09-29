import pytest

from netlogger.parser import extract_calls, extract_flags


@pytest.mark.parametrize("text,want", [
    ("Kilo Five Alpha Bravo Charlie, Dana in Georgetown.", ["K5ABC"]),
    ("This is K5ABC, Dana, Georgetown, no traffic.", ["K5ABC"]),
    ("Whiskey Five Bravo Oscar, Sam, short time.", ["W5BO"]),
    ("November Five X-ray Yankee Zulu with traffic", ["N5XYZ"]),
    ("K E 5 A B C checking in", ["KE5ABC"]),
    ("kilo echo five alpha bravo, Mike", ["KE5AB"]),
    ("Alpha Charlie Five Delta, mobile", ["AC5D"]),
    ("Whiskey Niner Oscar Oscar", ["W9OO"]),
    ("K5ABC and W5XYZ", ["K5ABC", "W5XYZ"]),
    ("Good evening everyone, this is net control.", []),
    ("I have one question for the group.", []),
])
def test_calls(text, want):
    assert extract_calls(text) == want


@pytest.mark.parametrize("text,want", [
    ("K5ABC with traffic", ["traffic"]),
    ("short time, W5BO", ["short_time"]),
    ("K5ABC please call me back later, short time", ["recheck", "short_time"]),
    ("K5ABC no traffic", []),
])
def test_flags(text, want):
    assert extract_flags(text) == want


# Real transcripts from a live test on base.en, 2026-09-29
@pytest.mark.parametrize("text,want", [
    ("W6UX-D, how are you doing? You're gone.", ["W6UXD"]),
    ("Whiskey Six Uniform X ray Delta", ["W6UXD"]),
    ("Whiskey Six's X-ray, checking in", ["W6X"]),   # possessive stripped; clipped call left for resolve()
    ("Kilo Echo Fife Alpha Bravo", ["KE5AB"]),
])
def test_real_world_slips(text, want):
    assert extract_calls(text) == want


def test_resolve_to_known_calls():
    from netlogger.parser import match_known, resolve
    known = {"W6UXD", "KE5KGX"}
    assert resolve("W6U", known) == "W6UXD"          # clipped
    assert resolve("W6X", known) == "W6UXD"          # dropped letter
    assert resolve("K5ABC", known) == "K5ABC"        # unknown stays as heard
    assert resolve("W6U", known | {"W6UAB"}) == "W6U"  # ambiguous: don't guess
    assert match_known("And five K G X.", known) == "KE5KGX"  # prefix lost entirely
    assert match_known("nothing useful here", known) is None
