from types import SimpleNamespace as Seg

from netlogger.audio import keep_text

P = "Ham radio net check-ins with callsigns in phonetics, like Kilo Five Alpha Bravo Charlie. Regulars: W6UXD."


def seg(text, no_speech=0.1, logprob=-0.3, ratio=1.2):
    return Seg(text=text, no_speech_prob=no_speech, avg_logprob=logprob, compression_ratio=ratio)


def test_real_checkin_kept():
    assert keep_text([seg("Whiskey Six Uniform X-ray Delta, checking in.")], P) == "Whiskey Six Uniform X-ray Delta, checking in."
    # a check-in that happens to use only prompt words is still real speech
    assert keep_text([seg("Kilo Five Alpha Bravo Charlie")], P) == "Kilo Five Alpha Bravo Charlie"


def test_prompt_echo_dropped():
    assert keep_text([seg("Niner. Stations. Niner. Stations. Niner.")], P) == ""
    assert keep_text([seg("Regulars: W6UXD.")], P) == ""
    assert keep_text([seg("Ham radio net check-ins with callsigns in phonetics")], P) == ""


def test_low_confidence_and_silence_dropped():
    assert keep_text([seg("Thank you.", no_speech=0.9, logprob=-0.8)], P) == ""
    assert keep_text([seg("blah blah blah blah", ratio=3.1)], P) == ""
    assert keep_text([seg("mumble", logprob=-1.5)], P) == ""
    # a bad segment doesn't sink a good one
    assert keep_text([seg("W6UXD with traffic."), seg("you", no_speech=0.95, logprob=-0.9)], P) == "W6UXD with traffic."


def test_stock_hallucinations_dropped():
    # all seen on a live node, 2026-09-29
    for junk in ["New videos every week!", "PFFT!", "Thanks for watching!"]:
        assert keep_text([seg(junk)], P) == ""
    assert keep_text([seg("This is KD5UEW. Who are you calling?")], P) == "This is KD5UEW. Who are you calling?"


def test_phrase_cut_keeps_real_call():
    assert keep_text([seg("W6UX-D, how are you doing? You're gone.")], P) == "W6UX-D, how are you doing? You're gone."
    assert keep_text([seg("W6UXD checking in. Thanks for watching!")], P) == "W6UXD checking in."
