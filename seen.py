"""Remember address tool results for this process.

Other plugins are not imported. transform_tool_result returns None.
A final-reply correction runs only when jp-charts would leave the reply as it is.
Hermes keeps the first non-empty transform_llm_output string, and jp-address
loads first, so a string here would hide that plugin's replacement.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

try:
    from . import turn_scope
except ImportError:
    import turn_scope

_SKIP = frozenset({"tool_search", "tool_describe", "tool_call"})
_CLAIM = re.compile(
    r"取得しました|確認しました|確認できます|で確認でき|を確認でき|を取得した|を確認した|"
    r"I (?:have )?(?:fetched|retrieved|confirmed)|"
    r"(?:have|has) been retrieved|retrieved successfully|successfully retrieved|"
    r"(?:have|has) been confirmed|(?:have|has) been verified|(?:have|has) been completed|"
    r"obtained using|"
    r"can be (?:confirmed|checked)",
    re.I,
)
# Same public tool names jp-charts uses to decide a fetch claim. Not an import.
_DATA_TOOLS = frozenset({
    "jp_corp_search",
    "jp_corp_profile",
    "edinet_search_filings",
    "edinet_financials",
    "edinet_save_document",
    "address_split",
    "subsidies_search",
    "subsidies_detail",
    "subsidies_watch_setup",
    "egov_law_search",
    "egov_law_article",
    "egov_law_revisions",
    "chart_render",
    "chart_validate",
    "chart_types",
})
_FORBIDDEN = re.compile(r"対象です")
_KEY_MARKERS = (
    "API_TOKEN",
    "API_KEY",
    "is not set",
    "Without this key",
    "Without this token",
    "free EDINET",
    "free personal API",
)
_LONG_DIGITS = re.compile(r"\d{10,}")
_GROUP_COMMA = re.compile(r"(?<=\d),(?=\d)")
_PREFS = (
    "神奈川県|和歌山県|鹿児島県|北海道|青森県|岩手県|宮城県|秋田県|山形県|福島県|"
    "茨城県|栃木県|群馬県|埼玉県|千葉県|東京都|新潟県|富山県|石川県|福井県|"
    "山梨県|長野県|岐阜県|静岡県|愛知県|三重県|滋賀県|京都府|大阪府|兵庫県|"
    "奈良県|鳥取県|島根県|岡山県|広島県|山口県|徳島県|香川県|愛媛県|高知県|"
    "福岡県|佐賀県|長崎県|熊本県|大分県|宮崎県|沖縄県"
)
_PREF = re.compile(_PREFS)
_ABSENCE = re.compile(
    r"The registered address was not returned, so it was not split\."
    r"|A prefecture was not named\."
    r"|住所は返っていない|住所は返っていません|分解していない|分解していません"
    r"|都道府県は書いていない|都道府県は書いていません"
)
_ABSENT_RULE = (
    "absent lists the parts that level did not resolve: "
    "level 0 lists pref, city, and town; level 1 lists city and town; level 2 lists town; "
    "level 3 lists none. A missing part is not written as 0."
)

_called: dict[str, set[str]] = {}
_notes: dict[str, list[str]] = {}
_digits: dict[str, set[str]] = {}
_facts: dict[str, dict] = {}


def _blank() -> dict:
    return {
        "pref": "",
        "address": "",
        "split": False,
        "asked_filing": False,
        "company_talk": False,
        "split_kind": "",
        "bare_errors": 0,
        "data_ok": False,
        "figure": False,
    }


def clear(session_id: Optional[str] = None) -> None:
    if session_id is None:
        _called.clear()
        _notes.clear()
        _digits.clear()
        _facts.clear()
        return
    _called.pop(session_id, None)
    _notes.pop(session_id, None)
    _digits.pop(session_id, None)
    _facts.pop(session_id, None)


def _parse(result: Any) -> Any:
    if isinstance(result, str):
        text = result.strip()
        if not text or text[0] not in "{[":
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
    return result


_NON_FIGURE = frozenset({"chart_types", "chart_validate"})


def in_address_turn(user_message: Any, conversation_history: Any = None) -> bool:
    """An address word, a prefecture, or address_split called in the previous turn."""
    return turn_scope.owns(user_message, conversation_history, "address")


def note_user(session_id: str, user_message: Any, conversation_history: Any = None) -> None:
    """Start this turn. A previous turn's tool record does not back this reply."""
    sid = session_id or ""
    scopes = turn_scope.domains(user_message, conversation_history)
    _called.pop(sid, None)
    _notes.pop(sid, None)
    _digits.pop(sid, None)
    facts = _blank()
    facts["asked_filing"] = "filing" in scopes
    facts["company_talk"] = "company" in scopes
    _facts[sid] = facts


def facts(session_id: str) -> dict:
    raw = _facts.get(session_id or "")
    if not raw:
        return _blank()
    return dict(raw)


def _long_digits(text: str) -> set[str]:
    return set(_LONG_DIGITS.findall(_GROUP_COMMA.sub("", text)))


def _bare_error(result: Any) -> bool:
    """A data-tool payload that is only an error: no next_step and no 10-digit number.

    Same condition jp-charts uses. This file does not import that plugin.
    """
    payload = _parse(result)
    if not isinstance(payload, dict):
        return False
    raw = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, default=str)
    if _long_digits(raw):
        return False
    note = payload.get("next_step") or ""
    if not isinstance(note, str) or not note.strip():
        error = str(payload.get("error") or "")
        kind = str(payload.get("kind") or "")
        if error == "token_missing" or kind == "api_key_missing_or_invalid":
            note = payload.get("message") or ""
        else:
            note = ""
    if isinstance(note, str) and note.strip():
        return False
    error = payload.get("error")
    status = str(payload.get("status") or "")
    if isinstance(error, str) and error.strip():
        return True
    if status in {"bad_args", "upstream", "error"}:
        return True
    return payload.get("ok") is False


def remember(session_id: str, tool_name: str, result: Any) -> None:
    if tool_name in _SKIP:
        return
    sid = session_id or ""
    _called.setdefault(sid, set()).add(tool_name or "")
    raw = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, default=str)
    bucket = _digits.setdefault(sid, set())
    for number in _long_digits(raw):
        bucket.add(number)
        if len(bucket) >= 400:
            break
    payload = _parse(result)
    found = _facts.setdefault(sid, _blank())
    if tool_name == "address_split":
        _note_split(found, payload)
    if isinstance(payload, dict):
        note = payload.get("next_step") or ""
        if not isinstance(note, str) or not note.strip():
            error = str(payload.get("error") or "")
            kind = str(payload.get("kind") or "")
            if error == "token_missing" or kind == "api_key_missing_or_invalid":
                note = payload.get("message") or ""
        if isinstance(note, str) and note.strip():
            notes = _notes.setdefault(sid, [])
            text = note.strip()[:1500]
            if text not in notes:
                notes.append(text)
            del notes[:-6]

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            pref = node.get("pref")
            if isinstance(pref, str) and pref.strip():
                found["pref"] = pref.strip()
                found["split"] = True
            for key in ("address", "location"):
                item = node.get(key)
                if isinstance(item, str) and item.strip() and not found["address"]:
                    found["address"] = item.strip()
            for item in node.values():
                walk(item)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    if (tool_name or "") in _DATA_TOOLS:
        if _bare_error(result):
            found["bare_errors"] = int(found.get("bare_errors") or 0) + 1
        elif _is_figure(tool_name or "", result):
            found["figure"] = True
            found["data_ok"] = True


def _note_split(found: dict, payload: Any) -> None:
    """Calling address_split is not a split. level 0, bad_args, and upstream stay distinct."""
    if not isinstance(payload, dict):
        return
    pref = payload.get("pref") if isinstance(payload.get("pref"), str) else ""
    if pref.strip():
        return
    status = str(payload.get("status") or "")
    error_type = str(payload.get("error_type") or "")
    level = payload.get("level")
    absent = payload.get("absent")
    kind = ""
    if status == "bad_args" or error_type == "bad_args":
        kind = "bad_args"
    elif status == "upstream":
        kind = "upstream"
    elif level == 0 or (isinstance(absent, list) and "pref" in absent):
        kind = "level0"
    if kind:
        found["split_kind"] = kind


def _split_sentence(kind: str) -> str:
    if kind == "level0":
        return (
            "address_split returned level 0. absent lists pref, city, and town. "
            "The address was not split. " + _ABSENT_RULE
        )
    if kind == "bad_args":
        return "address_split returned bad_args. The address was not split. " + _ABSENT_RULE
    if kind == "upstream":
        return "address_split returned upstream. The address was not split. " + _ABSENT_RULE
    return ""


def _edinet_key_unset() -> Optional[bool]:
    try:
        from agent.secret_scope import get_secret
    except Exception:
        return None
    try:
        value = get_secret("EDINET_API_KEY")
    except Exception:
        return None
    if value is None:
        return True
    return not bool(str(value).strip())


def _substantive(node: Any) -> bool:
    found = {"ok": False}

    def walk(item: Any) -> None:
        if found["ok"] or item is None:
            return
        if isinstance(item, dict):
            pref = item.get("pref")
            if isinstance(pref, str) and pref.strip():
                found["ok"] = True
                return
            industry = item.get("industry")
            if industry not in (None, "", [], {}):
                found["ok"] = True
                return
            for key in ("corporate_number", "metrics", "capital_stock", "law_title"):
                value = item.get(key)
                if value not in (None, "", [], {}, 0, False):
                    found["ok"] = True
                    return
            for value in item.values():
                walk(value)
        elif isinstance(item, list):
            for value in item:
                walk(value)

    walk(node)
    return found["ok"]


def _is_figure(tool_name: str, result: Any) -> bool:
    if tool_name not in _DATA_TOOLS or tool_name in _NON_FIGURE:
        return False
    if _bare_error(result):
        return False
    raw = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, default=str)
    if _long_digits(raw):
        return True
    if tool_name == "chart_render":
        return True
    return _substantive(_parse(result))


def _charts_will_rewrite(session_id: str, response_text: str) -> bool:
    """True when jp-charts would append its one line. Wording is not consulted."""
    if not isinstance(response_text, str) or not response_text.strip():
        return False
    sid = session_id or ""
    facts = _facts.get(sid, {})
    if facts.get("figure"):
        return False
    called = {name for name in _called.get(sid, ()) if name}
    area = called & _DATA_TOOLS
    if area and area <= {"address_split"}:
        return False
    return bool(area) or (
        bool(called) and (facts.get("company_talk") or facts.get("asked_filing"))
    )


def _scrub(session_id: str, text: str) -> Optional[str]:
    found = _facts.get(session_id or "", _blank())
    pref = found.get("pref") or ""
    if pref and _ABSENCE.search(text):
        fact = f"address_split returned {pref} and the address was split. " + _ABSENT_RULE
        replaced = _ABSENCE.sub(fact, text)
        doubled = fact + " " + fact
        while doubled in replaced:
            replaced = replaced.replace(doubled, fact)
        return replaced
    if pref:
        return None
    if not _PREF.search(text):
        return None
    replaced = _PREF.sub("", text)
    replaced = re.sub(r"[ \t]{2,}", " ", replaced).strip()
    sentence = _split_sentence(str(found.get("split_kind") or ""))
    if not sentence:
        sentence = (
            "The registered address was not returned, so it was not split. "
            + _ABSENT_RULE + " A prefecture was not named."
        )
    if "was not split" not in replaced:
        replaced = (replaced + " " + sentence).strip()
    elif found.get("split_kind") and found.get("split_kind") not in replaced:
        replaced = (replaced + " " + sentence).strip()
    return replaced


def correct(session_id: str, response_text: str) -> Optional[str]:
    if not isinstance(response_text, str) or not response_text.strip():
        return None
    if _charts_will_rewrite(session_id, response_text):
        return None
    if "address_split" not in _called.get(session_id or "", ()):
        return None
    return _scrub(session_id, response_text)
