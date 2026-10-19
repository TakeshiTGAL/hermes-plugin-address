"""Five argument shapes. Recorded sessions had no argument refusals."""
import json

import address
from test_address import _run


def test_prefecture_without_suffix_matches_tokyo():
    result, _calls = _run("東京千代田区霞が関2-1-2")
    assert result["level"] == 3
    assert result["pref"] == "東京都"
    assert result["city"] == "千代田区"


def test_fullwidth_digits_match_the_same_town():
    result, _calls = _run("東京都千代田区霞が関２－１－２")
    assert result["level"] == 3
    assert result["town"] == "霞が関二丁目"
    assert result["other"] == "1-2"


def test_osaka_without_fu_is_osaka():
    result, _calls = _run("大阪")
    assert result["level"] == 1
    assert result["pref"] == "大阪府"


def test_extra_argument_names_the_fix_without_the_key():
    out = json.loads(address.address_split({"address": "東京都千代田区", "level": 3}))
    text = json.dumps(out, ensure_ascii=False)
    assert out["ok"] is False
    assert out["error_type"] == "bad_args"
    assert "東京都千代田区霞が関2-1-2" in out["message"]
    assert "level" not in text


def test_ascii_letters_are_refused_with_an_example():
    result, calls = _run("TOKYO")
    text = json.dumps(result, ensure_ascii=False)
    assert result["ok"] is False
    assert result["error_type"] == "bad_args"
    assert "東京都千代田区霞が関2-1-2" in result["message"]
    assert "TOKYO" not in text
    assert len(calls) == 1
