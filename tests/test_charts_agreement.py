"""The address copy and jp-charts' public rewrite do not both change one reply.

jp-charts is loaded from the sibling checkout at one commit. This test calls
``rewrite``, which is not a private name. It does not import a private name
from that plugin.
"""

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

import address

# Filled after the jp-charts commit this copy was checked against.
CHARTS_SHA = "8eff93d1ea09a71975fa749116de633f1c952e88"
CHARTS_ROOT = Path(__file__).resolve().parents[2] / "hermes-plugin-charts"

SCENE = (
    "The process has successfully retrieved the company information. "
    "The results were obtained using the `jp_corp_search` tool. "
    "The company's information has been verified. "
    "The lookup has been completed. 愛知県"
)
LINE = (
    "Tool record: this turn returned no company, filing, address, subsidy, statute, or chart figure, "
    "so a number or a fetch claim in this reply is not from a tool result."
)


def _charts():
    # The isolated packaging run extracts this plugin alone. The sibling checkout is not in that tree.
    if not (CHARTS_ROOT / "reply_guard.py").is_file():
        pytest.skip("jp-charts reply_guard.py is not beside this checkout")
    try:
        head = subprocess.check_output(
            ["git", "-C", str(CHARTS_ROOT), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("jp-charts beside this checkout is not a git work tree")
    assert head == CHARTS_SHA, head
    spec = importlib.util.spec_from_file_location(
        "charts_reply_guard_pinned",
        CHARTS_ROOT / "reply_guard.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _exclusive(left, right):
    if isinstance(left, str):
        assert right is None
    if isinstance(right, str):
        assert left is None


def _same(charts, session_id, reply, *, user="", tools=()):
    address.seen.clear()
    charts.clear()
    if user:
        address.seen.note_user(session_id, user)
        charts.note_user(session_id, user)
    for name, payload in tools:
        raw = json.dumps(payload)
        address.seen.remember(session_id, name, raw)
        charts.remember(session_id, name, raw)
    address_out = address.seen.correct(session_id, reply)
    charts_out = charts.rewrite(session_id, reply)
    _exclusive(address_out, charts_out)
    will = address.seen._charts_will_rewrite(session_id, reply)
    assert will is (isinstance(charts_out, str))
    return address_out, charts_out


def test_charts_rewrite_and_address_correct_are_exclusive():
    charts = _charts()

    address_out, charts_out = _same(
        charts,
        "s-scene",
        SCENE,
        user="有報の連結の売上",
        tools=(("browser_exec", {"error": "chrome"}),),
    )
    assert address_out is None
    assert isinstance(charts_out, str)
    assert SCENE in charts_out
    assert LINE in charts_out
    assert "WEEK0060" not in charts_out
    assert "That claim is removed" not in charts_out

    bare = "The corporate number has been retrieved successfully. 愛知県"
    address_out, charts_out = _same(
        charts,
        "s-bare",
        bare,
        tools=(("jp_corp_search", {"error": "api", "message": "gBizINFO returned HTTP 500."}),),
    )
    assert address_out is None
    assert isinstance(charts_out, str)
    assert bare in charts_out
    assert LINE in charts_out
    assert "WEEK0060" not in charts_out

    address_out, charts_out = _same(
        charts,
        "s-split",
        "登記の所在地は愛知県です。",
        tools=(("address_split", {"level": 0, "absent": ["pref", "city", "town"], "other": "豊田"}),),
    )
    assert isinstance(address_out, str)
    assert charts_out is None
    assert "愛知県" not in address_out
    assert "was not split" in address_out
