"""Log collector must tolerate non-UTF8 Redis field values."""
from app.services.logging.collector import _as_text, _parse_entry


def test_as_text_replaces_invalid_utf8():
    raw = b"hello\xbdworld"
    text = _as_text(raw)
    assert "hello" in text
    assert "world" in text
    assert "\ufffd" in text


def test_parse_entry_accepts_replacement_chars():
    # After redis encoding_errors=replace, fields arrive as str with U+FFFD.
    payload = '{"mode":"block","ua":"bad\ufffdbyte","ts":1}'
    entry = _parse_entry({"data": payload})
    assert entry is not None
    assert entry["mode"] == "block"
    assert entry["ua"] == "bad\ufffdbyte"


def test_parse_entry_bytes_invalid_utf8_still_json_if_rest_valid():
    # Pure binary in a JSON string value becomes replacement chars after decode.
    prefix = b'{"mode":"observe","ua":"'
    suffix = b'"}'
    raw = prefix + b"x\xbd\xbey" + suffix
    entry = _parse_entry({"data": raw})
    assert entry is not None
    assert entry["mode"] == "observe"
    assert "\ufffd" in entry["ua"]


def test_parse_entry_malformed_goes_none():
    assert _parse_entry({"data": "{not-json"}) is None
    assert _parse_entry({"data": b"\xff\xfe"}) is None
