"""Split one Japanese address to town level. Stdlib only. No disk cache."""

from __future__ import annotations

import bisect
import gzip
import http.client
import io
import json
import os
import time
import unicodedata
import urllib.error
import urllib.request
from typing import Callable
from urllib.parse import quote, urlsplit

TOOLSET = "jp_address"
# The list file is this URL. The base is the same string without the final ".json".
_LIST_URL = "https://japanese-addresses-v2.geoloniamaps.com/api/ja.json"
DEFAULT_BASE = _LIST_URL[: -len(".json")]
# Cloudflare answers 403 error 1010 to Python-urllib's default User-Agent (2026-10-08).
USER_AGENT = "jp-address/0.1.0"
# Both the socket timeout and the deadline for one whole GET, in seconds.
TIMEOUT = 30
LIMIT = 8_000_000
MAX_CHARS = 400

ATTRIBUTION = (
    "Geolonia 住所データ（CC BY 4.0 https://creativecommons.org/licenses/by/4.0/）。"
    "本データは、「アドレス・ベース・レジストリ」（デジタル庁）をもとに株式会社 Geolonia が作成したものです。"
    "「アドレス・ベース・レジストリ」（デジタル庁）（https://dataset.address-br.digital.go.jp）をもとに株式会社 Geolonia が作成し、jp-address が町丁目までを選択した。"
)

MSG_EXTRA = "address_split takes only an address string."
MSG_LENGTH = "The address must be a string of 400 characters or fewer."
MSG_URL = "JP_ADDRESS_BASE_URL is not a usable origin."
MSG_CITY = "This municipality name is in more than one prefecture. Include the prefecture."
MSG_MUNI = "This name matches more than one municipality. Include the county."
MSG_TOWN = "More than one town matches the same span."
MSG_TOWN_LEN = "More than one town matches this address at different lengths."
MSG_UPSTREAM = "The address file could not be read."

Fetch = Callable[[str], tuple[int, bytes]]


class TransportError(Exception):
    def __init__(self, status: int | None) -> None:
        self.status = status


class SchemaError(Exception):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Do not call the Location host. urllib would otherwise follow 301/302/303/307/308."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        raise urllib.error.HTTPError(req.full_url, code, msg, headers, fp)


def usable_base(raw: str) -> str | None:
    """scheme, host, optional port, and a non-empty path. No query, fragment, userinfo, or trailing slash."""
    if not isinstance(raw, str) or raw == "":
        return None
    if any(ord(ch) < 32 or ch.isspace() for ch in raw):
        return None
    if "?" in raw or "#" in raw or "\\" in raw:
        return None
    parts = urlsplit(raw)
    scheme = parts.scheme.lower()
    if scheme not in ("https", "http"):
        return None
    if parts.username is not None or parts.password is not None:
        return None
    if parts.query or parts.fragment:
        return None
    host = parts.hostname
    if not host or parts.path == "" or parts.path.endswith("/"):
        return None
    if scheme == "http" and host.lower() not in ("127.0.0.1", "localhost"):
        return None
    return raw


def list_url(base: str) -> str:
    return base + ".json"


def town_url(base: str, pref: str, city: str) -> str:
    return base + "/" + quote(pref, safe="") + "/" + quote(city, safe="") + ".json"


def _header(headers, name: str):
    if headers is None:
        return None
    getter = getattr(headers, "get", None)
    if getter is None:
        return None
    value = getter(name)
    if value is None:
        value = getter(name.lower())
    return value


def _content_length(headers, status: int) -> int | None:
    raw = _header(headers, "Content-Length")
    if raw is None:
        return None
    text = str(raw).strip()
    if text == "" or len(text) > 20 or not text.isdigit():
        raise TransportError(status)
    return int(text)


def _encoding(headers) -> str:
    raw = _header(headers, "Content-Encoding")
    if raw is None or str(raw).strip() == "":
        return "identity"
    parts = [part.strip().lower() for part in str(raw).split(",") if part.strip()]
    if parts in (["identity"], []):
        return "identity"
    if parts == ["gzip"]:
        return "gzip"
    raise TransportError(None)  # status filled by the caller when known


def _read_capped(fp, limit: int, deadline: float | None = None) -> bytes:
    """Read the body. A slow trickle stops at the deadline instead of running forever.

    read1 returns what one socket read gave, so the deadline is looked at between
    socket reads. read would wait for a whole 65536 bytes and could sit there for
    as many socket timeouts as the sender wants to spend.
    """
    chunks: list[bytes] = []
    total = 0
    read1 = getattr(fp, "read1", None)
    while True:
        if deadline is not None and time.monotonic() >= deadline:
            raise _OverLimit()
        block = read1(65536) if read1 is not None else fp.read(65536)
        if not block:
            break
        total += len(block)
        if total > limit:
            raise _OverLimit()
        chunks.append(block)
    return b"".join(chunks)


class _OverLimit(Exception):
    """The body was over the cap, or the request ran past its deadline."""


def _gunzip_capped(raw: bytes, limit: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as gz:
            while True:
                block = gz.read(65536)
                if not block:
                    break
                total += len(block)
                if total > limit:
                    raise _OverLimit()
                chunks.append(block)
    except _OverLimit:
        raise
    except Exception as exc:
        raise TransportError(None) from exc
    return b"".join(chunks)


def read_body(status: int, headers, fp, limit: int = LIMIT, deadline: float | None = None) -> bytes:
    """Return the body for a finished response. Over the cap, past the deadline, or a foreign encoding, raises TransportError."""
    try:
        declared = _content_length(headers, status)
    except TransportError:
        raise TransportError(status) from None
    if declared is not None and declared > limit:
        raise TransportError(status)
    if status != 200:
        try:
            raw = _read_capped(fp, limit, deadline)
        except _OverLimit:
            raise TransportError(status) from None
        if declared is not None and len(raw) != declared:
            raise TransportError(status)
        return raw
    try:
        encoding = _encoding(headers)
    except TransportError:
        raise TransportError(status) from None
    try:
        raw = _read_capped(fp, limit, deadline)
    except _OverLimit:
        raise TransportError(status) from None
    if declared is not None and len(raw) != declared:
        raise TransportError(status)
    if encoding == "gzip":
        try:
            return _gunzip_capped(raw, limit)
        except _OverLimit:
            raise TransportError(status) from None
        except TransportError:
            raise TransportError(status) from None
    return raw


def http_get(url: str) -> tuple[int, bytes]:
    """One GET. Proxies in the environment are not used. Redirects are not followed.

    TIMEOUT is both the socket timeout and the deadline for the whole GET. The
    deadline is read before the connection and before every 64 KiB block, so one
    socket wait can still be in flight when it passes.
    """
    deadline = time.monotonic() + TIMEOUT
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"},
        method="GET",
    )
    try:
        resp = opener.open(req, timeout=TIMEOUT)
    except urllib.error.HTTPError as exc:
        resp = exc
    except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException):
        raise TransportError(None) from None
    try:
        status = int(getattr(resp, "status", None) or resp.getcode())
        body = read_body(status, resp.headers, resp, deadline=deadline)
    finally:
        resp.close()
    return status, body


def _point(value):
    """[longitude, latitude] from the file, returned as (lat, lng). Out-of-range pairs are dropped."""
    if not isinstance(value, list) or len(value) != 2:
        return None
    lng, lat = value[0], value[1]
    if isinstance(lng, bool) or isinstance(lat, bool):
        return None
    if not isinstance(lng, (int, float)) or not isinstance(lat, (int, float)):
        return None
    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
        return None
    return (lat, lng)


def _parse_city(row: dict) -> dict:
    """File name is county + city + ward. A listed county also matches without the county."""
    city = row.get("city")
    if not isinstance(city, str) or city == "":
        raise SchemaError()
    county = row.get("county")
    ward = row.get("ward")
    county_s = county if isinstance(county, str) else ""
    ward_s = ward if isinstance(ward, str) else ""
    official = county_s + city + ward_s
    short = city + ward_s
    names = [official] if short == official else [official, short]
    return {"official": official, "names": names, "point": _point(row.get("point"))}


def _json_object(body: bytes):
    if len(body) > LIMIT:
        raise SchemaError()
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise SchemaError() from None
    except RecursionError:
        # Nested arrays deeper than the interpreter limit. Treat the file as unreadable.
        raise SchemaError() from None
    return payload


def parse_prefs(body: bytes) -> list[dict]:
    payload = _json_object(body)
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise SchemaError()
    prefs: list[dict] = []
    for row in payload["data"]:
        if not isinstance(row, dict):
            raise SchemaError()
        name = row.get("pref")
        cities = row.get("cities")
        if not isinstance(name, str) or name == "" or not isinstance(cities, list):
            raise SchemaError()
        parsed = []
        for city in cities:
            if not isinstance(city, dict):
                raise SchemaError()
            parsed.append(_parse_city(city))
        prefs.append({"name": name, "point": _point(row.get("point")), "cities": parsed})
    return prefs


def _chome_n(value) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if 1 <= value <= 99:
        return value
    return None


def _part(value) -> str:
    """Town-file names are normalized the same way as the input before matching."""
    if isinstance(value, str) and value:
        return _normalize(value)
    return ""


# A lot number may follow the town in kanji. 番地 starts with 番, which is already a boundary.
_BOUNDARY_KANJI = frozenset("〇零一二三四五六七八九十百千")
# Longer suffixes first, so 丁目 is not split into 丁.
_NUM_SUFFIXES = ("丁目", "地割", "番町", "条", "線", "号")


def _boundary_ok(text: str, length: int) -> bool:
    """The character after a town name must be a lot marker or the end.

    Lot markers are an ASCII digit, a kanji numeral, 番 (and therefore 番地),
    号, -, 字, or 丁.
    """
    if length <= 0 or length > len(text):
        return False
    if length == len(text):
        return True
    nxt = text[length]
    if "0" <= nxt <= "9" or nxt in ("番", "号", "-", "字", "丁"):
        return True
    return nxt in _BOUNDARY_KANJI


def _arabic_to_kanji(number: int) -> str | None:
    """1–99 as a place-name numeral. 0 is 零, matching rows such as 零号. Above 99 stays unconverted."""
    if number < 0 or number > 99:
        return None
    if number == 0:
        return "零"
    ones = "一二三四五六七八九"
    if number < 10:
        return ones[number - 1]
    tens, rest = divmod(number, 10)
    head = "十" if tens == 1 else ones[tens - 1] + "十"
    if rest == 0:
        return head
    return head + ones[rest - 1]


def _expanded_units(text: str) -> list[tuple[int, str]]:
    """Split text into (original_end, expanded) units.

    A run of ASCII digits immediately before 条, 線, 号, 地割, 丁目, or 番町
    becomes one unit whose text is the kanji numeral plus that suffix.
    宮の森1条 is compared as 宮の森一条. Digits before a hyphen are left as digits,
    so 霞が関2-1-2 and 霞が関21-2 are not rewritten. NFKC has already folded
    fullwidth digits.
    """
    units: list[tuple[int, str]] = []
    index = 0
    size = len(text)
    while index < size:
        if "0" <= text[index] <= "9":
            end = index + 1
            while end < size and "0" <= text[end] <= "9":
                end += 1
            suffix = ""
            for candidate in _NUM_SUFFIXES:
                if text.startswith(candidate, end):
                    suffix = candidate
                    break
            if suffix:
                kanji = _arabic_to_kanji(int(text[index:end]))
                if kanji is not None:
                    stop = end + len(suffix)
                    units.append((stop, kanji + suffix))
                    index = stop
                    continue
        units.append((index + 1, text[index]))
        index += 1
    return units


def _prefix_end(units: list[tuple[int, str]], cand: str) -> int | None:
    """Original end index if cand equals a unit-aligned prefix of the expanded text."""
    if not cand:
        return None
    acc = ""
    for end, piece in units:
        acc += piece
        if len(acc) < len(cand):
            if not cand.startswith(acc):
                return None
            continue
        if acc == cand:
            return end
        return None
    return None


def _canonical(row: dict) -> str:
    """Normalized town name. The displayed town keeps the file's own spelling."""
    oaza_s = _part(row.get("oaza_cho"))
    chome_s = _part(row.get("chome"))
    koaza_s = _part(row.get("koaza"))
    if oaza_s:
        return oaza_s + chome_s + koaza_s
    return koaza_s


def _head_name(row: dict) -> str:
    """The row's normalized name with its 丁目 removed. A koaza-only row keeps its koaza."""
    oaza_s = _part(row.get("oaza_cho"))
    koaza_s = _part(row.get("koaza"))
    if oaza_s:
        return oaza_s + koaza_s
    return koaza_s


def _has_longer_name(sorted_names: list[str], name: str) -> bool:
    if not name:
        return False
    index = bisect.bisect_right(sorted_names, name)
    return index < len(sorted_names) and sorted_names[index].startswith(name)


def _town_match_len(row: dict, text: str, units: list[tuple[int, str]] | None = None) -> tuple[int, str]:
    """Return (original length, kind). kind is loose for an Arabic or hyphen form without 丁目.

    The kanji reading of digits before 条, 線, 号, 地割, 丁目, or 番町 is also tried.
    That length is still an index into the original text, so `other` stays aligned.
    """
    if not isinstance(row, dict):
        return 0, ""
    oaza_s = _part(row.get("oaza_cho"))
    chome_s = _part(row.get("chome"))
    koaza_s = _part(row.get("koaza"))
    best = 0
    kind = ""

    def take(cand: str, cand_kind: str) -> None:
        nonlocal best, kind
        n = len(cand)
        if n > best and cand and text.startswith(cand) and _boundary_ok(text, n):
            best = n
            kind = cand_kind

    name = ""
    if oaza_s:
        name = oaza_s + chome_s + koaza_s
        take(name, "name")
        # A koaza is part of the name. Arabic chome forms apply only when the row has no koaza.
        number = _chome_n(row.get("chome_n"))
        if koaza_s == "" and number is not None:
            digits = str(number)
            take(oaza_s + digits + "丁目", "name")
            take(oaza_s + digits + "-", "loose")
            bare = oaza_s + digits
            if text.startswith(bare):
                nxt = text[len(bare):len(bare) + 1]
                if nxt in ("", "番", "-", "号") or nxt in _BOUNDARY_KANJI:
                    take(bare, "loose")
    elif koaza_s:
        name = koaza_s
        take(name, "name")
    if name:
        expanded = units if units is not None else _expanded_units(text)
        end = _prefix_end(expanded, name)
        if end is not None and end > best and _boundary_ok(text, end):
            best = end
            kind = "name"
    return best, kind


def _id_of(row: dict):
    value = row.get("machiaza_id")
    if isinstance(value, str):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    return None


def _with_attribution(body: dict) -> dict:
    body["attribution"] = ATTRIBUTION
    return body


def _upstream(status: int | None) -> dict:
    message = MSG_UPSTREAM
    if isinstance(status, int) and not isinstance(status, bool) and status >= 100:
        message = f"{MSG_UPSTREAM} HTTP {status}."
    return _with_attribution({"status": "upstream", "message": message})


def _bad(message: str) -> dict:
    return _with_attribution({"status": "bad_args", "message": message})


def _normalize(text: str) -> str:
    """NFKC, then drop every whitespace character: space, U+3000, tab, newline, carriage return."""
    folded = unicodedata.normalize("NFKC", text)
    return "".join(ch for ch in folded if not ch.isspace())


def _longest(items: list, text: str, name_of) -> list:
    best: list = []
    best_len = 0
    for item in items:
        name = name_of(item)
        if isinstance(name, str) and name and text.startswith(name) and len(name) >= best_len:
            if len(name) > best_len:
                best = []
                best_len = len(name)
            best.append(item)
    return best


def _longest_cities(cities: list, text: str) -> list[tuple[dict, str]]:
    best: list[tuple[dict, str]] = []
    best_len = 0
    for city in cities:
        for name in city["names"]:
            if name and text.startswith(name) and len(name) >= best_len:
                if len(name) > best_len:
                    best = []
                    best_len = len(name)
                best.append((city, name))
    return best


def _ambiguous_municipalities(hits: list[tuple[dict, str]]) -> dict:
    names: list[str] = []
    for city, _matched in hits:
        official = city["official"]
        if official not in names:
            names.append(official)
    return _with_attribution({
        "status": "ambiguous_city",
        "message": MSG_MUNI,
        "municipalities": names,
    })


def _point_obj(lat_lng, level: int) -> dict:
    lat, lng = lat_lng
    return {"lat": lat, "lng": lng, "level": level}


def _attach_point(body: dict, chosen, city_point, pref_point) -> None:
    if chosen is not None:
        body["point"] = _point_obj(chosen[0], chosen[1])
        return
    if city_point is not None:
        body["point"] = _point_obj(city_point, 2 if body["level"] >= 2 else 1)
        return
    if pref_point is not None:
        body["point"] = _point_obj(pref_point, 1)


def _load(fetch: Fetch, url: str) -> tuple[int, bytes]:
    try:
        return fetch(url)
    except TransportError:
        raise
    except Exception as exc:
        raise TransportError(None) from exc


def split_address(address, *, base: str, fetch: Fetch) -> dict:
    if not isinstance(address, str) or len(address) > MAX_CHARS:
        return _bad(MSG_LENGTH)
    text = _normalize(address)
    if text == "":
        return _with_attribution({"level": 0, "other": ""})

    try:
        status, body = _load(fetch, list_url(base))
    except TransportError as exc:
        return _upstream(exc.status)
    if status != 200:
        return _upstream(status)
    try:
        prefs = parse_prefs(body)
    except SchemaError:
        return _upstream(status)

    pref_hits = _longest(prefs, text, lambda item: item["name"])
    if len({item["name"] for item in pref_hits}) > 1:
        return _upstream(200)
    pref = pref_hits[0] if pref_hits else None
    if pref is not None:
        rest = text[len(pref["name"]):]
        city_hits = _longest_cities(pref["cities"], rest)
        # Two rows with the same name stay ambiguous even when their points agree.
        if len(city_hits) >= 2:
            return _ambiguous_municipalities(city_hits)
        if not city_hits:
            body_out = {"level": 1, "pref": pref["name"], "other": rest}
            _attach_point(body_out, None, None, pref["point"])
            return _with_attribution(body_out)
        city, matched = city_hits[0]
        pref_point = pref["point"]
        city_point = city["point"]
        rest = rest[len(matched):]
    else:
        hits = []
        best_len = 0
        for item in prefs:
            for city in item["cities"]:
                for name in city["names"]:
                    if name and text.startswith(name) and len(name) >= best_len:
                        if len(name) > best_len:
                            hits = []
                            best_len = len(name)
                        hits.append((item, city, name))
        pref_names = []
        for item, _city, _name in hits:
            if item["name"] not in pref_names:
                pref_names.append(item["name"])
        if len(pref_names) >= 2:
            return _with_attribution({
                "status": "ambiguous_city",
                "message": MSG_CITY,
                "prefectures": pref_names,
            })
        if len(hits) >= 2:
            return _ambiguous_municipalities([(city, name) for _item, city, name in hits])
        if not hits:
            return _with_attribution({"level": 0, "other": text})
        pref, city, matched = hits[0]
        pref_point = pref["point"]
        city_point = city["point"]
        rest = text[len(matched):]

    try:
        status, body = _load(fetch, town_url(base, pref["name"], city["official"]))
    except TransportError as exc:
        return _upstream(exc.status)
    if status != 200:
        return _upstream(status)
    try:
        payload = _json_object(body)
    except SchemaError:
        return _upstream(status)
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        return _upstream(status)

    rows = payload["data"]
    for row in rows:
        # One bad element fails the whole file, the same way a bad city fails the list.
        if not isinstance(row, dict):
            return _upstream(status)

    # Names of the rows that carry no 丁目. A koaza-only row such as 中山 counts
    # here the same way an oaza row such as 原別 does.
    no_chome_names: set[str] = set()
    names: list[str] = []
    for row in rows:
        canon = _canonical(row)
        names.append(canon)
        if canon and not _part(row.get("chome")):
            no_chome_names.add(canon)
    sorted_names = sorted({name for name in names if name})
    units = _expanded_units(rest)
    prepared: list[tuple[dict, str, int, str]] = []
    for row, canon in zip(rows, names):
        matched, kind = _town_match_len(row, rest, units)
        prepared.append((row, canon, matched, kind))

    matched_names = {canon for _row, canon, matched, _kind in prepared if matched and canon}

    def longer_matched(name: str) -> bool:
        for other in matched_names:
            if len(other) > len(name) and other.startswith(name):
                return True
        return False

    # A short town is not a level-3 success when a longer sibling exists and the
    # input matches none of them. A prefix of such a rejected town is not a
    # success either: 大字泊村 must not swallow 字糸泊 after 字糸泊山ノ上 rejects it.
    unsafe: set[str] = set()
    for name in matched_names:
        if _has_longer_name(sorted_names, name) and not longer_matched(name):
            unsafe.add(name)
    grew = True
    while grew:
        grew = False
        extra: list[str] = []
        for name in matched_names:
            if name in unsafe:
                continue
            for bad in unsafe:
                if len(bad) > len(name) and bad.startswith(name):
                    extra.append(name)
                    break
        for name in extra:
            if name not in unsafe:
                unsafe.add(name)
                grew = True

    safe = [
        (row, matched, kind)
        for row, canon, matched, kind in prepared
        if matched and canon not in unsafe
    ]
    best_len = 0
    best_rows: list[tuple[dict, str, int]] = []
    for row, matched, kind in safe:
        if matched > best_len:
            best_len = matched
            best_rows = [(row, kind, matched)]
        elif matched == best_len:
            best_rows.append((row, kind, matched))
    # When a row with no 丁目 carries the same name, an Arabic number, a hyphen or
    # 番地 does not pick the chome: 宮ケ丘3番地1 and 中山1 are ambiguous. Only a
    # written 丁目, in kanji or Arabic digits, picks it. Ids are the matching rows.
    loose_heads: list[str] = []
    for row, kind, _matched in best_rows:
        head = _head_name(row)
        if kind == "loose" and head in no_chome_names and head not in loose_heads:
            loose_heads.append(head)
    if loose_heads:
        chosen: list[tuple[dict, int]] = []
        for row, matched, _kind in safe:
            head = _head_name(row)
            if head not in loose_heads:
                continue
            is_bare = not _part(row.get("chome"))
            if is_bare or matched == best_len:
                chosen.append((row, matched))
        if len(chosen) >= 2:
            lengths = {matched for _row, matched in chosen}
            return _with_attribution({
                "status": "ambiguous_town",
                "message": MSG_TOWN if len(lengths) == 1 else MSG_TOWN_LEN,
                "towns": [_town_name(row) for row, _matched in chosen],
                "machiaza_id": [_id_of(row) for row, _matched in chosen],
            })
    if len(best_rows) >= 2:
        return _with_attribution({
            "status": "ambiguous_town",
            "message": MSG_TOWN,
            "towns": [_town_name(row) for row, _kind, _matched in best_rows],
            "machiaza_id": [_id_of(row) for row, _kind, _matched in best_rows],
        })
    if not best_rows:
        body_out = {"level": 2, "pref": pref["name"], "city": city["official"], "other": rest}
        _attach_point(body_out, None, city_point, pref_point)
        return _with_attribution(body_out)

    row = best_rows[0][0]
    other = rest[best_len:]
    if other.startswith("-"):
        other = other[1:]
    town_point = _point(row.get("point"))
    body_out = {
        "level": 3,
        "pref": pref["name"],
        "city": city["official"],
        "town": _town_name(row),
        "other": other,
    }
    if town_point is not None:
        body_out["point"] = _point_obj(town_point, 3)
    else:
        _attach_point(body_out, None, city_point, pref_point)
    return _with_attribution(body_out)


def _town_name(row: dict) -> str:
    oaza = row.get("oaza_cho")
    chome = row.get("chome")
    koaza = row.get("koaza")
    oaza_s = oaza if isinstance(oaza, str) and oaza else ""
    chome_s = chome if isinstance(chome, str) and chome else ""
    koaza_s = koaza if isinstance(koaza, str) and koaza else ""
    if oaza_s:
        return oaza_s + chome_s + koaza_s
    return koaza_s


def address_split(args, **_kwargs) -> str:
    if not isinstance(args, dict) or set(args) - {"address"}:
        return json.dumps(_bad(MSG_EXTRA), ensure_ascii=False)
    if "JP_ADDRESS_BASE_URL" in os.environ:
        base = usable_base(os.environ["JP_ADDRESS_BASE_URL"])
        if base is None:
            return json.dumps(_bad(MSG_URL), ensure_ascii=False)
    else:
        base = DEFAULT_BASE
    result = split_address(args.get("address"), base=base, fetch=http_get)
    return json.dumps(result, ensure_ascii=False)


def register(ctx) -> None:
    ctx.register_tool(
        name="address_split",
        toolset=TOOLSET,
        schema={
            "name": "address_split",
            "description": (
                "Split one Japanese address into prefecture, city, town, and the remainder. "
                "The only argument is address, a string of 400 characters or fewer. "
                "Levels are 0, 1, 2, or 3. "
                "When a point is present, the source lists longitude first; results name lat and lng. "
                "A point can be coarser than the town and is not a rooftop geocode. "
                "At most two GET requests are sent, and only after the base URL is accepted. "
                "Plain http is refused except for 127.0.0.1 and localhost. "
                "The matched prefecture and municipality names go into the URL path; the house number does not. "
                "No API key is read or sent. "
                "A result with no level has status ambiguous_town, ambiguous_city, upstream, or bad_args. "
                "An ambiguous_town result lists the towns it could not choose between. "
                "Every result carries an attribution string that has to be shown with the result."
            ),
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "address": {
                        "type": "string",
                        "description": "One Japanese address. 400 characters or fewer.",
                    },
                },
                "required": ["address"],
            },
        },
        handler=address_split,
    )
