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
