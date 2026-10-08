"""Offline checks for the frozen jp-address acceptance rows."""

import ast
import json
from pathlib import Path

import yaml

import address

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://example.test/api/ja"
KASUMI = [139.750413, 35.675551]
CHIYODA = [139.753634, 35.694003]
TOKYO = [139.691717, 35.689568]
YOTSUYA = [139.730722, 35.687428]
HTML = "<html>NoSuchKey cloudflareinsights</html>"


def _b(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False).encode()


def _prefs():
    return [
        {"pref": "北海道", "cities": [{"city": "札幌市", "ward": "中央区", "point": [141.35, 43.06]}]},
        {
            "pref": "東京都",
            "point": TOKYO,
            "pref_r": "Tokyo",
            "cities": [
                {"city": "千代田区", "point": CHIYODA, "code": "131016"},
                {"city": "府中市", "point": [139.48, 35.67]},
            ],
        },
        {"pref": "大阪府", "cities": [{"city": "大阪市"}]},
        {"pref": "広島県", "cities": [{"city": "府中市"}, {"city": "府中町"}]},
        {"pref": "京都府", "cities": [{"city": "京都市"}]},
    ]


def _kasumi_rows():
    return [
        {
            "machiaza_id": "0002001",
            "oaza_cho": "霞が関",
            "chome": "一丁目",
            "chome_n": 1,
            "point": [139.752558, 35.673944],
            "rsdt": True,
            "csv_ranges": {"地番": {"start": 1, "length": 2}},
        },
        {
            "machiaza_id": "0002002",
            "oaza_cho": "霞が関",
            "chome": "二丁目",
            "chome_n": 2,
            "point": KASUMI,
            "rsdt": True,
            "csv_ranges": {"地番": {"start": 3, "length": 4}},
        },
        {
            "machiaza_id": "0002003",
            "oaza_cho": "霞が関",
            "chome": "三丁目",
            "chome_n": 3,
            "point": [139.746988, 35.671825],
            "rsdt": True,
            "csv_ranges": {"地番": {"start": 5, "length": 6}},
        },
        {"machiaza_id": "0000101", "oaza_cho": None, "koaza": "四谷見付", "point": YOTSUYA},
        {"machiaza_id": "0060001", "oaza_cho": "猿楽町", "chome": "一丁目", "chome_n": 1},
        {"machiaza_id": "ake", "oaza_cho": "旭ケ丘", "chome": "一丁目", "chome_n": 1, "point": [1, 2]},
    ]


def _run(text, towns=None, prefs=None, extra_routes=None):
    calls = []
    prefs = _prefs() if prefs is None else prefs
    towns = _kasumi_rows() if towns is None else towns
    routes = {address.list_url(BASE): (200, _b({"data": prefs}))}
    routes[address.town_url(BASE, "東京都", "千代田区")] = (200, _b({"data": towns}))
    routes[address.town_url(BASE, "北海道", "札幌市中央区")] = (200, _b({"data": []}))
    routes[address.town_url(BASE, "東京都", "府中市")] = (200, _b({"data": []}))
    routes[address.town_url(BASE, "京都府", "京都市")] = (200, _b({"data": []}))
    if extra_routes:
        routes.update(extra_routes)

    def fetch(url):
        calls.append(url)
        if url not in routes:
            return (404, HTML.encode())
        item = routes[url]
        if isinstance(item, Exception):
            raise item
        return item

    return address.split_address(text, base=BASE, fetch=fetch), calls


def test_names_and_register_surface():
    src = (ROOT / "address.py").read_text() + (ROOT / "__init__.py").read_text()
    for banned in (
        "subprocess",
        "plugin_data",
        "geolonia-api-key",
        "GEOLONIA_API_KEY",
        "register_command",
        "urlopen(",
        "request_tool_approval",
    ):
        assert banned not in src
    tree = ast.parse((ROOT / "__init__.py").read_text())
    imported = [
        (node.level, node.module)
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    ]
    assert imported == [(1, "address"), (0, "address")]
    init_src = (ROOT / "__init__.py").read_text()
    assert "from .address import register as register_tool" in init_src
    assert "from address import register as register_tool" in init_src

    class Ctx:
        def __init__(self):
            self.calls = []

        def register_tool(self, **kwargs):
            self.calls.append(kwargs)

    ctx = Ctx()
    address.register(ctx)
    assert [call["name"] for call in ctx.calls] == ["address_split"]
    call = ctx.calls[0]
    assert call["toolset"] == "jp_address"
    assert call.get("override") is not True
    assert list(call["schema"]["parameters"]["properties"]) == ["address"]
    assert call["schema"]["parameters"]["additionalProperties"] is False
    assert (
        "A result with no level has status ambiguous_town, ambiguous_city, upstream, or bad_args."
        in call["schema"]["description"]
    )


def test_catalog_description_states_the_facts():
    """Facts the catalog text must carry. The wording itself is free to change."""
    manifest = yaml.safe_load((ROOT / "plugin.yaml").read_text())
    desc = manifest["description"]
    assert len(desc) <= 1500
    assert not desc.endswith("\n")
    assert desc.count("Disclosure —") == 1
    assert "Disclosure:" not in desc
    disclosure = desc.split("Disclosure —", 1)[1]
    assert "address_split" in desc
    assert "japanese-addresses-v2.geoloniamaps.com" in disclosure and "JP_ADDRESS_BASE_URL" in disclosure
    assert "no API key" in disclosure
    assert "gateway" in disclosure and "hermes tools" in disclosure and "no approval" in disclosure
    assert "CC BY 4.0" in desc
    assert "Not tested from a Hermes model." in desc
    assert manifest["name"] == "jp-address"
    assert manifest["version"] == "0.1.0"
    assert manifest["manifest_version"] == 2
    assert manifest["requires_hermes"] == ">=0.21.4"
    assert manifest["python_dependencies"] == []
    assert manifest["provides_tools"] == ["address_split"]
    assert manifest["provides_hooks"] == []


def test_readme_required_sentences():
    readme = (ROOT / "README.md").read_text()
    assert address.ATTRIBUTION in readme
    assert "現在、制限無しで無料公開をしていますが、様子を見ながら公開の停止や変更などを行うことがあります。商用稼働は、ご自身でデータを作成しホスティングすることを強くおすすめします。" in readme
    assert "Geolonia では有償で管理・ホスティングするサービスがありますので、ご利用の方はお問い合わせください。" in readme
    assert "314034" in readme and "47" in readme and "124" in readme
    assert "139.750413" in readme and "35.675551" in readme
    assert "札幌市中央区.json" in readme and "札幌市.json" in readme
    assert "北佐久郡軽井沢町" in readme
    assert "They do not open a socket." not in readme
    assert "http.server" in readme and "127.0.0.1" in readme
    assert "hermes tools" in readme
    assert "refused under cron" not in readme
    assert "Unofficial" not in readme and "非公式" not in readme and "not affiliated" not in readme
    assert "pip install" not in readme and "--yes-deps" not in readme
    assert "商用禁止" not in readme
    assert "8_000_000" in readme and "30 seconds" in readme and "no retry" in readme
    assert "Town-file names get that same normalization" in readme
    assert "does not become the one-character town" in readme
    assert "There is no daily limit." in readme
    assert "大字泊村字メノコ走" in readme
    assert "was not called from a Hermes model" in readme
    assert "not a port of normalize-japanese-addresses" in readme
    assert "The source lists longitude first; results name lat and lng." in readme


def test_three_chome_forms_and_no_secret_fields():
    for text in (
        "東京都千代田区霞が関2-1-2",
        "東京都千代田区霞が関二丁目1-2",
        "東京都千代田区霞が関2丁目1-2",
        "東京都　千代田区 霞が関2-1-2",
    ):
        result, calls = _run(text)
        assert result["level"] == 3
        assert result["pref"] == "東京都"
        assert result["city"] == "千代田区"
        assert result["town"] == "霞が関二丁目"
        assert result["other"] == "1-2"
        assert result["point"] == {"lat": 35.675551, "lng": 139.750413, "level": 3}
        assert result["attribution"] == address.ATTRIBUTION
        assert "csv_ranges" not in result and "rsdt" not in result and "machiaza_id" not in result
        assert len(calls) == 2
        assert calls[1].endswith("%E6%9D%B1%E4%BA%AC%E9%83%BD/%E5%8D%83%E4%BB%A3%E7%94%B0%E5%8C%BA.json")
        assert "1-2" not in calls[1]
        assert not calls[1].endswith(".txt")
        dumped = json.dumps(result, ensure_ascii=False)
        assert "csv_ranges" not in dumped and "rsdt" not in dumped


def test_bare_kasumi_and_wrong_prefecture_do_not_guess():
    bare, calls = _run("東京都千代田区霞が関")
    assert bare["level"] == 2 and bare["other"] == "霞が関" and "town" not in bare
    assert bare["point"] == {"lat": 35.694003, "lng": 139.753634, "level": 2}
    assert len(calls) == 2
    stayed, calls = _run("東京都大阪市")
    assert stayed["level"] == 1 and stayed["pref"] == "東京都" and stayed["other"] == "大阪市"
    assert "city" not in stayed and len(calls) == 1
    assert all("大阪" not in url for url in calls)


def test_arabic_chome_rules():
    missed, _ = _run("東京都千代田区霞が関21-2")
    assert missed["level"] == 2 and missed["other"] == "霞が関21-2" and "town" not in missed
    kanji_only = [{"oaza_cho": "霞が関", "chome": "二丁目", "machiaza_id": "k"}]
    hit, _ = _run("東京都千代田区霞が関二丁目1-2", towns=kanji_only)
    assert hit["level"] == 3 and hit["town"] == "霞が関二丁目" and hit["other"] == "1-2"
    miss, _ = _run("東京都千代田区霞が関2丁目1-2", towns=kanji_only)
    assert miss["level"] == 3 and miss["town"] == "霞が関二丁目" and miss["other"] == "1-2"
    hyphen_only, _ = _run("東京都千代田区霞が関2-1-2", towns=kanji_only)
    assert hyphen_only["level"] == 2 and "town" not in hyphen_only
    flagged = [{"oaza_cho": "霞が関", "chome": "二丁目", "chome_n": True, "machiaza_id": "b"}]
    no_bool, _ = _run("東京都千代田区霞が関2丁目1-2", towns=flagged)
    assert no_bool["level"] == 3 and no_bool["town"] == "霞が関二丁目"
    decimal = [{"oaza_cho": "霞が関", "chome": "二丁目", "chome_n": 2.5, "machiaza_id": "d"}]
    no_decimal, _ = _run("東京都千代田区霞が関2丁目1-2", towns=decimal)
    assert no_decimal["level"] == 3 and no_decimal["town"] == "霞が関二丁目"
    wide, _ = _run("東京都千代田区霞が関２－１－２")
    assert wide["town"] == "霞が関二丁目" and wide["other"] == "1-2"


def test_koaza_and_longest_town_and_ambiguous_town():
    yotsuya, _ = _run("東京都千代田区四谷見付")
    assert yotsuya["level"] == 3 and yotsuya["town"] == "四谷見付"
    assert yotsuya["point"] == {"lat": 35.687428, "lng": 139.730722, "level": 3}
    both = [
        {"oaza_cho": "霞が関", "machiaza_id": "short", "point": [0, 1]},
        {"oaza_cho": "霞が関", "chome": "二丁目", "chome_n": 2, "machiaza_id": "long", "point": KASUMI},
    ]
    longer, _ = _run("東京都千代田区霞が関二丁目1-2", towns=both)
    assert longer["town"] == "霞が関二丁目" and longer["other"] == "1-2"
    tied = [
        {"oaza_cho": "同町", "machiaza_id": "a", "point": [1, 2]},
        {"oaza_cho": "同町", "machiaza_id": "b", "point": [3, 4]},
    ]
    amb, calls = _run("東京都千代田区同町1", towns=tied)
    assert amb["status"] == "ambiguous_town"
    assert amb["message"] == address.MSG_TOWN
    assert amb["machiaza_id"] == ["a", "b"]
    assert amb["towns"] == ["同町", "同町"]
    assert "level" not in amb and "point" not in amb and len(calls) == 2


def test_oaza_and_koaza_keep_the_longest_name():
    prefs = [{
        "pref": "北海道",
        "cities": [{"city": "泊村", "county": "古宇郡", "point": [140.498857, 43.063212]}],
    }]
    rows = [
        {"machiaza_id": "0004000", "oaza_cho": "大字泊村", "point": [140.509332, 43.093158]},
        {"machiaza_id": "0004101", "oaza_cho": "大字泊村", "koaza": "字メノコ走"},
        {"machiaza_id": "0004102", "oaza_cho": "大字泊村", "koaza": "字モヘル川"},
        {"machiaza_id": "0004106", "oaza_cho": "大字泊村", "koaza": "字糸泊", "point": [140.51, 43.08]},
        {"machiaza_id": "0004107", "oaza_cho": "大字泊村", "koaza": "字糸泊山ノ上"},
        {"machiaza_id": "koaza-only", "koaza": "糸泊", "point": [140.1, 43.01]},
    ]
    route = {address.town_url(BASE, "北海道", "古宇郡泊村"): (200, _b({"data": rows}))}
    bare, calls = _run("北海道古宇郡泊村大字泊村", prefs=prefs, towns=[], extra_routes=route)
    assert bare["level"] == 2 and "town" not in bare and bare["other"] == "大字泊村"
    assert bare["city"] == "古宇郡泊村"
    assert bare["point"] == {"lat": 43.063212, "lng": 140.498857, "level": 2}
    assert "machiaza_id" not in bare and "status" not in bare and len(calls) == 2
    alone_rows = [row for row in rows if row["machiaza_id"] == "0004000"]
    alone_route = {address.town_url(BASE, "北海道", "古宇郡泊村"): (200, _b({"data": alone_rows}))}
    alone, _ = _run("北海道古宇郡泊村大字泊村", prefs=prefs, towns=[], extra_routes=alone_route)
    assert alone["level"] == 3 and alone["town"] == "大字泊村" and alone["other"] == ""
    assert alone["point"] == {"lat": 43.093158, "lng": 140.509332, "level": 3}
    long, _ = _run("北海道古宇郡泊村大字泊村字メノコ走", prefs=prefs, towns=[], extra_routes=route)
    assert long["level"] == 3 and long["town"] == "大字泊村字メノコ走" and long["other"] == ""
    assert long["point"] == {"lat": 43.063212, "lng": 140.498857, "level": 2}
    ito, _ = _run("北海道古宇郡泊村大字泊村字糸泊", prefs=prefs, towns=[], extra_routes=route)
    assert ito["level"] == 2 and "town" not in ito and ito["other"] == "大字泊村字糸泊"
    assert ito["point"] == {"lat": 43.063212, "lng": 140.498857, "level": 2}
    yama, _ = _run("北海道古宇郡泊村大字泊村字糸泊山ノ上", prefs=prefs, towns=[], extra_routes=route)
    assert yama["town"] == "大字泊村字糸泊山ノ上" and yama["point"]["level"] == 2
    only, _ = _run("北海道古宇郡泊村糸泊", prefs=prefs, towns=[], extra_routes=route)
    assert only["level"] == 3 and only["town"] == "糸泊"
    koaza_rows = [row for row in rows if row["machiaza_id"] != "0004000"]
    route_koaza = {address.town_url(BASE, "北海道", "古宇郡泊村"): (200, _b({"data": koaza_rows}))}
    short, _ = _run("北海道古宇郡泊村大字泊村", prefs=prefs, towns=[], extra_routes=route_koaza)
    assert short["level"] == 2 and short["other"] == "大字泊村" and "town" not in short
    mixed = rows + [{
        "machiaza_id": "chome-koaza",
        "oaza_cho": "大字泊村",
        "chome": "一丁目",
        "chome_n": 1,
        "koaza": "字甲",
        "point": [140.2, 43.02],
    }]
    route_mixed = {address.town_url(BASE, "北海道", "古宇郡泊村"): (200, _b({"data": mixed}))}
    arabic, _ = _run("北海道古宇郡泊村大字泊村1-2", prefs=prefs, towns=[], extra_routes=route_mixed)
    assert arabic["level"] == 2 and "town" not in arabic and arabic["other"] == "大字泊村1-2"
    named, _ = _run("北海道古宇郡泊村大字泊村一丁目字甲", prefs=prefs, towns=[], extra_routes=route_mixed)
    assert named["town"] == "大字泊村一丁目字甲" and named["point"]["level"] == 3
    same = [
        {"machiaza_id": "a", "oaza_cho": "大字泊村", "koaza": "字甲", "point": [1, 2]},
        {"machiaza_id": "b", "oaza_cho": "大字泊村", "koaza": "字甲", "point": [3, 4]},
    ]
    route_same = {address.town_url(BASE, "北海道", "古宇郡泊村"): (200, _b({"data": same}))}
    tied_koaza, _ = _run("北海道古宇郡泊村大字泊村字甲", prefs=prefs, towns=[], extra_routes=route_same)
    assert tied_koaza["status"] == "ambiguous_town" and tied_koaza["message"] == address.MSG_TOWN
    assert tied_koaza["machiaza_id"] == ["a", "b"]
    assert "point" not in tied_koaza


def test_folds_that_are_not_applied():
    miss, _ = _run("東京都千代田区旭ヶ丘一丁目")
    assert miss["level"] == 2 and "旭ケ丘" not in miss["other"] and miss["other"].startswith("旭ヶ丘")
    banchi, _ = _run("東京都千代田区霞が関二丁目1番2号")
    assert banchi["level"] == 3 and banchi["other"] == "1番2号"
    listed = [{"pref": "北海道", "cities": [{"city": "余市町", "county": "余市郡"}]}]
    yoichi_url = address.town_url(BASE, "北海道", "余市郡余市町")
    yoichi_route = {yoichi_url: (200, _b({"data": []}))}
    with_county, calls = _run("北海道余市郡余市町", prefs=listed, towns=[], extra_routes=yoichi_route)
    assert with_county["level"] == 2 and with_county["city"] == "余市郡余市町" and with_county["other"] == ""
    assert len(calls) == 2 and calls[1].rsplit("/", 1)[-1] == yoichi_url.rsplit("/", 1)[-1]
    without, calls = _run("北海道余市町", prefs=listed, towns=[], extra_routes=yoichi_route)
    assert without["level"] == 2 and without["city"] == "余市郡余市町" and without["other"] == "" and len(calls) == 2
    absent = [{"pref": "北海道", "cities": [{"city": "余市町"}]}]
    invented, calls = _run("北海道余市郡余市町", prefs=absent, towns=[])
    assert invented["level"] == 1 and invented["other"] == "余市郡余市町" and len(calls) == 1
    old_kanji = [{"pref": "長野県", "cities": [{"city": "軽井沢町", "county": "北佐久郡"}]}]
    folded, calls = _run("長野県軽井澤町", prefs=old_kanji, towns=[])
    assert folded["level"] == 1 and folded["other"] == "軽井澤町" and len(calls) == 1
    kyoto, calls = _run("京都府寺町通京都市", towns=[])
    assert kyoto["level"] == 1 and kyoto["other"] == "寺町通京都市" and len(calls) == 1
    roman, calls = _run("Tokyo千代田区")
    assert roman["level"] == 0 and len(calls) == 1


def test_upstream_shapes_are_not_a_successful_split():
    html, _ = _run("東京都千代田区霞が関2-1-2", extra_routes={
        address.town_url(BASE, "東京都", "千代田区"): (404, HTML.encode()),
    })
    dumped = json.dumps(html, ensure_ascii=False)
    assert html["status"] == "upstream" and "404" in html["message"]
    assert "<html>" not in dumped and "NoSuchKey" not in dumped and "cloudflareinsights" not in dumped
    assert html["attribution"] == address.ATTRIBUTION and "level" not in html
    for body in (b"", b"<html></html>", _b({"error": "no"}), _b({"meta": {}}), b"[1,2]", b"null"):
        got, _ = _run("東京都千代田区霞が関", extra_routes={
            address.town_url(BASE, "東京都", "千代田区"): (200, body),
        })
        assert got["status"] == "upstream" and "level" not in got
        assert got.get("other") != "東京都千代田区霞が関"
    empty, _ = _run("東京都千代田区霞が関2-1-2", towns=[])
    assert empty["level"] == 2 and empty["status"] if False else empty["level"] == 2
    assert "status" not in empty and "town" not in empty
    broken, calls = _run("東京都千代田区霞が関", extra_routes={
        address.town_url(BASE, "東京都", "千代田区"): (502, b"<html>bad</html>"),
    })
    assert broken["status"] == "upstream" and "502" in broken["message"] and "level" not in broken
    assert len(calls) == 2
    listed, calls = _run("東京都千代田区", extra_routes={
        address.list_url(BASE): (500, b"<html>no</html>"),
    })
    assert listed["status"] == "upstream" and "level" not in listed and len(calls) == 1
    bad_row, calls = _run("大阪府大阪市", prefs=[{"pref": "", "cities": []}, {"pref": "大阪府", "cities": [{"city": "大阪市"}]}])
    assert bad_row["status"] == "upstream" and len(calls) == 1
    not_dict, _ = _run("東京都千代田区霞が関", towns=["not-a-dict"])
    assert not_dict["status"] == "upstream" and "level" not in not_dict and "town" not in not_dict
    mixed_row, _ = _run(
        "東京都千代田区霞が関",
        towns=[{"oaza_cho": "霞が関", "chome": "二丁目", "chome_n": 2, "point": KASUMI}, 1],
    )
    assert mixed_row["status"] == "upstream" and "level" not in mixed_row


def test_ambiguous_city_and_omitted_prefecture():
    amb, calls = _run("府中市1")
    assert amb["status"] == "ambiguous_city"
    assert amb["message"] == address.MSG_CITY
    assert amb["prefectures"] == ["東京都", "広島県"]
    assert len(calls) == 1 and "level" not in amb
    one, calls = _run("千代田区霞が関2-1-2")
    assert one["level"] == 3 and one["pref"] == "東京都" and one["town"] == "霞が関二丁目"
    assert len(calls) == 2
    foreign, calls = _run("1600 Pennsylvania")
    assert foreign["level"] == 0 and foreign["status"] if False else foreign["level"] == 0
    assert "status" not in foreign and len(calls) == 1
    chosen, calls = _run("東京都府中市1-2")
    assert chosen["level"] == 2 and chosen["city"] == "府中市" and len(calls) == 2


def test_missing_point_is_coarser_and_never_invented():
    rows = [
        {"oaza_cho": "霞が関", "chome": "二丁目", "chome_n": 2, "machiaza_id": "n"},
    ]
    got, _ = _run("東京都千代田区霞が関2-1-2", towns=rows)
    assert got["level"] == 3 and got["town"] == "霞が関二丁目"
    assert got["point"] == {"lat": 35.694003, "lng": 139.753634, "level": 2}
    prefs = [{
        "pref": "東京都",
        "point": TOKYO,
        "cities": [{"city": "千代田区"}],
    }]
    cityless, _ = _run("東京都千代田区霞が関2-1-2", prefs=prefs, towns=rows)
    assert cityless["level"] == 3
    assert cityless["point"] == {"lat": 35.689568, "lng": 139.691717, "level": 1}
    none, _ = _run("東京都千代田区霞が関2-1-2", prefs=[{"pref": "東京都", "cities": [{"city": "千代田区"}]}], towns=rows)
    assert none["level"] == 3 and "point" not in none
    assert "[0, 0]" not in json.dumps(none)
    # A pair outside the globe is not a coordinate. It falls through like a missing one.
    for bad in ([139.75, 95.0], [-181.0, 35.68], [139.75, -90.5]):
        wild = [{"oaza_cho": "霞が関", "chome": "二丁目", "chome_n": 2, "machiaza_id": "n", "point": bad}]
        got, _ = _run("東京都千代田区霞が関2-1-2", towns=wild)
        assert got["level"] == 3
        assert got["point"] == {"lat": 35.694003, "lng": 139.753634, "level": 2}
    edge = [{"oaza_cho": "霞が関", "chome": "二丁目", "chome_n": 2, "machiaza_id": "n", "point": [180, 90]}]
    kept, _ = _run("東京都千代田区霞が関2-1-2", towns=edge)
    assert kept["point"] == {"lat": 90.0, "lng": 180.0, "level": 3}


def test_sapporo_path_and_no_third_get():
    got, calls = _run("北海道札幌市中央区北一条")
    assert got["level"] == 2 and got["city"] == "札幌市中央区"
    assert calls[1].endswith("/%E5%8C%97%E6%B5%B7%E9%81%93/%E6%9C%AD%E5%B9%8C%E5%B8%82%E4%B8%AD%E5%A4%AE%E5%8C%BA.json")
    assert not calls[1].endswith("/%E6%9C%AD%E5%B9%8C%E5%B8%82.json")
    _, calls = _run("東京都千代田区霞が関2-1-2")
    assert len(calls) == 2 and all(not url.endswith(".txt") for url in calls)


def test_county_filename_matches_with_and_without_county():
    prefs = [{
        "pref": "長野県",
        "cities": [{"city": "軽井沢町", "county": "北佐久郡", "point": [138.6, 36.34]}],
    }]
    towns = [{"oaza_cho": "軽井沢", "machiaza_id": "k", "point": [138.61, 36.35]}]
    url = address.town_url(BASE, "長野県", "北佐久郡軽井沢町")
    routes = {url: (200, _b({"data": towns}))}
    for text in ("長野県軽井沢町軽井沢1", "長野県北佐久郡軽井沢町軽井沢1"):
        got, calls = _run(text, prefs=prefs, towns=towns, extra_routes=routes)
        assert got["level"] == 3 and got["city"] == "北佐久郡軽井沢町" and got["town"] == "軽井沢"
        assert got["other"] == "1" and got["point"]["lat"] == 36.35
        assert len(calls) == 2 and calls[1].rsplit("/", 1)[-1] == url.rsplit("/", 1)[-1]


def test_same_name_rows_are_ambiguous_even_when_points_agree():
    prefs = [{
        "pref": "北海道",
        "cities": [
            {"city": "泊村", "county": "古宇郡", "point": [140.5, 43.06]},
            {"city": "泊村", "county": "国後郡", "point": [145.5, 43.33]},
        ],
    }]
    got, calls = _run("北海道泊村", prefs=prefs, towns=[])
    assert got["status"] == "ambiguous_city" and got["message"] == address.MSG_MUNI
    assert got["municipalities"] == ["古宇郡泊村", "国後郡泊村"]
    assert "level" not in got and "point" not in got and "prefectures" not in got
    assert len(calls) == 1
    prefs[0]["cities"][1]["point"] = [140.5, 43.06]
    same, calls = _run("北海道泊村", prefs=prefs, towns=[])
    assert same["message"] == address.MSG_MUNI and "point" not in same and len(calls) == 1
    dup = [{
        "pref": "北海道",
        "cities": [
            {"city": "泊村", "county": "古宇郡", "point": [140.5, 43.06]},
            {"city": "泊村", "county": "古宇郡", "point": [140.5, 43.06]},
        ],
    }]
    agreed, calls = _run("北海道古宇郡泊村", prefs=dup, towns=[])
    assert agreed["message"] == address.MSG_MUNI and "point" not in agreed and len(calls) == 1
    one, calls = _run("北海道古宇郡泊村1", prefs=prefs, towns=[], extra_routes={
        address.town_url(BASE, "北海道", "古宇郡泊村"): (200, _b({"data": []})),
    })
    assert one["level"] == 2 and one["city"] == "古宇郡泊村" and one["other"] == "1" and len(calls) == 2
    bare, calls = _run("泊村", prefs=prefs, towns=[])
    assert bare["message"] == address.MSG_MUNI and len(calls) == 1


def test_arabic_or_hyphen_is_ambiguous_beside_a_chomeless_row():
    rows = [
        {"machiaza_id": "bare", "oaza_cho": "宮ケ丘", "point": [141.30, 43.054]},
        {"machiaza_id": "1", "oaza_cho": "宮ケ丘", "chome": "一丁目", "chome_n": 1, "point": [141.31, 43.055]},
        {"machiaza_id": "3", "oaza_cho": "宮ケ丘", "chome": "三丁目", "chome_n": 3, "point": [141.32, 43.056]},
    ]
    url = address.town_url(BASE, "北海道", "札幌市中央区")
    routes = {url: (200, _b({"data": rows}))}
    ban, calls = _run("北海道札幌市中央区宮ケ丘3番地1", extra_routes=routes)
    assert ban["status"] == "ambiguous_town" and ban["message"] == address.MSG_TOWN_LEN
    assert ban["machiaza_id"] == ["bare", "3"]
    assert "level" not in ban and "point" not in ban and len(calls) == 2
    hyphen, _ = _run("北海道札幌市中央区宮ケ丘3-1", extra_routes=routes)
    assert hyphen["status"] == "ambiguous_town" and hyphen["message"] == address.MSG_TOWN_LEN
    assert hyphen["machiaza_id"] == ["bare", "3"]
    number_mark, _ = _run("北海道札幌市中央区宮ケ丘3号", extra_routes=routes)
    assert number_mark["status"] == "ambiguous_town" and number_mark["message"] == address.MSG_TOWN_LEN
    assert number_mark["machiaza_id"] == ["bare", "3"]
    explicit, _ = _run("北海道札幌市中央区宮ケ丘3丁目1", extra_routes=routes)
    assert explicit["level"] == 3 and explicit["town"] == "宮ケ丘三丁目" and explicit["other"] == "1"
    assert explicit["point"] == {"lat": 43.056, "lng": 141.32, "level": 3}
    kanji, _ = _run("北海道札幌市中央区宮ケ丘三丁目1", extra_routes=routes)
    assert kanji["level"] == 3 and kanji["town"] == "宮ケ丘三丁目" and kanji["other"] == "1"
    variant, _ = _run("北海道札幌市中央区宮ヶ丘3番地1", extra_routes=routes)
    assert variant["level"] == 2 and variant["other"] == "宮ヶ丘3番地1" and "town" not in variant
    extra = rows + [
        {"machiaza_id": "koaza", "oaza_cho": "宮ケ丘", "koaza": "字甲"},
    ]
    routes_extra = {url: (200, _b({"data": extra}))}
    still, _ = _run("北海道札幌市中央区宮ケ丘3番地1", extra_routes=routes_extra)
    assert still["machiaza_id"] == ["bare", "3"]


def test_town_boundary_and_normalized_town_names():
    morioka = [{
        "pref": "岩手県",
        "cities": [{"city": "盛岡市", "point": [141.154183, 39.701795]}],
    }]
    morioka_rows = [
        {"machiaza_id": "0000159", "koaza": "舘", "point": [141.157656, 39.640269]},
        {"machiaza_id": "0146000", "oaza_cho": "館向町", "point": [141.129598, 39.719955]},
        {"machiaza_id": "0007000", "oaza_cho": "飯岡新田", "point": [141.137034, 39.665898]},
        {"machiaza_id": "0007101", "oaza_cho": "飯岡新田", "koaza": "１地割"},
        {"machiaza_id": "0007102", "oaza_cho": "飯岡新田", "koaza": "１０地割"},
        {"machiaza_id": "0034000", "oaza_cho": "門", "point": [141.180286, 39.669513]},
        {"machiaza_id": "0034002", "oaza_cho": "門", "chome": "二丁目", "chome_n": 2, "point": [141.172549, 39.664992]},
        {"machiaza_id": "0034101", "oaza_cho": "門", "koaza": "字角下"},
        {"machiaza_id": "0000355", "koaza": "大塚", "point": [141.174844, 39.713869]},
    ]
    morioka_url = address.town_url(BASE, "岩手県", "盛岡市")
    morioka_routes = {morioka_url: (200, _b({"data": morioka_rows}))}
    tate, _ = _run("岩手県盛岡市舘向町1-1", prefs=morioka, towns=[], extra_routes=morioka_routes)
    assert tate["level"] == 2 and "town" not in tate and tate["other"] == "舘向町1-1"
    assert tate["point"] == {"lat": 39.701795, "lng": 141.154183, "level": 2}
    wari, _ = _run("岩手県盛岡市飯岡新田１地割", prefs=morioka, towns=[], extra_routes=morioka_routes)
    assert wari["level"] == 3 and wari["town"] == "飯岡新田１地割" and wari["other"] == ""
    assert wari["point"] == {"lat": 39.701795, "lng": 141.154183, "level": 2}
    ascii_wari, _ = _run("岩手県盛岡市飯岡新田1地割", prefs=morioka, towns=[], extra_routes=morioka_routes)
    assert ascii_wari["town"] == "飯岡新田１地割"
    ten, _ = _run("岩手県盛岡市飯岡新田１０地割", prefs=morioka, towns=[], extra_routes=morioka_routes)
    assert ten["town"] == "飯岡新田１０地割"
    gate, _ = _run("岩手県盛岡市門2-3", prefs=morioka, towns=[], extra_routes=morioka_routes)
    assert gate["status"] == "ambiguous_town" and gate["message"] == address.MSG_TOWN_LEN
    assert gate["machiaza_id"] == ["0034000", "0034002"]
    assert "point" not in gate
    kanji_lot, _ = _run("岩手県盛岡市大塚三番地", prefs=morioka, towns=[], extra_routes=morioka_routes)
    assert kanji_lot["level"] == 3 and kanji_lot["town"] == "大塚" and kanji_lot["other"] == "三番地"
    folded, _ = _run("岩手県盛岡市大塚", prefs=morioka, towns=[], extra_routes=morioka_routes)
    assert folded["level"] == 3 and folded["town"] == "大塚"
    assert folded["point"] == {"lat": 39.713869, "lng": 141.174844, "level": 3}
    old, _ = _run("岩手県盛岡市館向町1-1", prefs=morioka, towns=[], extra_routes=morioka_routes)
    assert old["level"] == 3 and old["town"] == "館向町" and old["other"] == "1-1"
    assert old["point"] == {"lat": 39.719955, "lng": 141.129598, "level": 3}

    sendai = [{
        "pref": "宮城県",
        "cities": [{"city": "仙台市", "ward": "青葉区", "point": [140.870378, 38.269087]}],
    }]
    sendai_rows = [
        {"machiaza_id": "0000111", "koaza": "宮", "point": [140.757467, 38.263244]},
        {"machiaza_id": "0016001", "oaza_cho": "宮町", "chome": "一丁目", "chome_n": 1},
    ]
    sendai_url = address.town_url(BASE, "宮城県", "仙台市青葉区")
    miyagi, _ = _run(
        "宮城県仙台市青葉区宮城町1",
        prefs=sendai,
        towns=[],
        extra_routes={sendai_url: (200, _b({"data": sendai_rows}))},
    )
    assert miyagi["level"] == 2 and "town" not in miyagi and miyagi["other"] == "宮城町1"
    assert miyagi["city"] == "仙台市青葉区"
    assert miyagi["point"] == {"lat": 38.269087, "lng": 140.870378, "level": 2}

    iwaki = [{
        "pref": "福島県",
        "cities": [{"city": "いわき市", "point": [140.887687, 37.050456]}],
    }]
    iwaki_rows = [
        {"machiaza_id": "0041000", "oaza_cho": "内郷御厩町", "point": [140.873671, 37.043307]},
        {"machiaza_id": "0041001", "oaza_cho": "内郷御厩町", "chome": "一丁目", "chome_n": 1, "point": [140.867936, 37.044585]},
        {"machiaza_id": "0041101", "oaza_cho": "内郷御厩町", "koaza": "１丁目"},
        {"machiaza_id": "0041102", "oaza_cho": "内郷御厩町", "koaza": "大畑"},
    ]
    iwaki_url = address.town_url(BASE, "福島県", "いわき市")
    iwaki_routes = {iwaki_url: (200, _b({"data": iwaki_rows}))}
    fullwidth, _ = _run("福島県いわき市内郷御厩町１丁目", prefs=iwaki, towns=[], extra_routes=iwaki_routes)
    assert fullwidth["status"] == "ambiguous_town" and fullwidth["message"] == address.MSG_TOWN
    assert fullwidth["machiaza_id"] == ["0041001", "0041101"]
    assert "point" not in fullwidth and "town" not in fullwidth
    kanji_chome, _ = _run("福島県いわき市内郷御厩町一丁目", prefs=iwaki, towns=[], extra_routes=iwaki_routes)
    assert kanji_chome["level"] == 3 and kanji_chome["town"] == "内郷御厩町一丁目"
    lot, _ = _run("福島県いわき市内郷御厩町1-1", prefs=iwaki, towns=[], extra_routes=iwaki_routes)
    assert lot["status"] == "ambiguous_town" and lot["message"] == address.MSG_TOWN_LEN
    assert lot["machiaza_id"] == ["0041000", "0041001"]

    aomori = [{
        "pref": "青森県",
        "cities": [{"city": "青森市", "point": [140.74732, 40.822358]}],
    }]
    aomori_rows = [
        {"machiaza_id": "0085003", "oaza_cho": "沖館", "chome": "三丁目", "chome_n": 3, "point": [140.722882, 40.83742]},
        {"machiaza_id": "0085101", "oaza_cho": "沖館", "koaza": "字篠田"},
    ]
    okidate, _ = _run(
        "青森県青森市沖館3-1-1",
        prefs=aomori,
        towns=[],
        extra_routes={address.town_url(BASE, "青森県", "青森市"): (200, _b({"data": aomori_rows}))},
    )
    assert okidate["level"] == 3 and okidate["town"] == "沖館三丁目" and okidate["other"] == "1-1"
    assert okidate["point"] == {"lat": 40.83742, "lng": 140.722882, "level": 3}
    assert "machiaza_id" not in okidate
    kanji_ban, _ = _run(
        "青森県青森市沖館三丁目一番一号",
        prefs=aomori,
        towns=[],
        extra_routes={address.town_url(BASE, "青森県", "青森市"): (200, _b({"data": aomori_rows}))},
    )
    assert kanji_ban["level"] == 3 and kanji_ban["town"] == "沖館三丁目" and kanji_ban["other"] == "一番一号"
    marunouchi, _ = _run(
        "東京都千代田区丸の内一丁目一番一号",
        towns=[{
            "machiaza_id": "0011001",
            "oaza_cho": "丸の内",
            "chome": "一丁目",
            "chome_n": 1,
            "point": [139.767201, 35.68156],
        }],
    )
    assert marunouchi["level"] == 3 and marunouchi["town"] == "丸の内一丁目"
    assert marunouchi["other"] == "一番一号"
    assert marunouchi["point"] == {"lat": 35.68156, "lng": 139.767201, "level": 3}


def test_arguments_length_and_blank(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("normalized")

    monkeypatch.setattr(address.unicodedata, "normalize", boom)
    calls = []

    def fetch(url):
        calls.append(url)
        raise AssertionError("fetched")

    long = address.split_address("あ" * 401, base=BASE, fetch=fetch)
    assert long["status"] == "bad_args" and long["message"] == address.MSG_LENGTH
    assert calls == []
    for value in (None, 1, True, "東京都".encode(), ["東京都"]):
        got = address.split_address(value, base=BASE, fetch=fetch)
        assert got["message"] == address.MSG_LENGTH and "level" not in got
    monkeypatch.undo()
    for text in (" \u3000 ", "\n", "\t", " \r\n\t\u3000"):
        blank, calls2 = _run(text)
        assert blank["level"] == 0 and blank["other"] == "" and calls2 == []
        assert blank["attribution"] == address.ATTRIBUTION


def test_line_breaks_and_tabs_are_removed_before_matching():
    for text in (
        "東京都\n千代田区\n霞が関2-1-2",
        "東京都\t千代田区\t霞が関2-1-2",
        "東京都\r\n千代田区 \u3000霞が関2-1-2",
    ):
        got, calls = _run(text)
        assert got["level"] == 3 and got["pref"] == "東京都" and got["city"] == "千代田区"
        assert got["town"] == "霞が関二丁目" and got["other"] == "1-2"
        assert len(calls) == 2


def test_handler_env_and_extra_args(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GEOLONIA_API_KEY", "supersecretvalue")
    seen = []

    def fetch(url):
        seen.append(url)
        if url.endswith("/api/ja.json"):
            return (200, _b({"data": _prefs()}))
        return (200, _b({"data": _kasumi_rows()}))

    monkeypatch.setattr(address, "http_get", fetch)
    monkeypatch.delenv("JP_ADDRESS_BASE_URL", raising=False)
    default = json.loads(address.address_split({"address": "東京都千代田区霞が関2-1-2"}))
    assert default["town"] == "霞が関二丁目"
    assert address.DEFAULT_BASE == "https://japanese-addresses-v2.geoloniamaps.com/api/ja"
    assert seen[0] == address.list_url(address.DEFAULT_BASE)
    assert "supersecretvalue" not in json.dumps(seen) and "supersecretvalue" not in json.dumps(default)
    extra = json.loads(address.address_split({"address": "東京都", "level": 3}))
    assert extra["message"] == address.MSG_EXTRA
    assert len(seen) == 2
    for bad in ("", "https://example.test/api/ja/", "https://example.test/api/ja?x=1",
                "https://user:pw@example.test/api/ja", "https://example.test/api/ja#x",
                "http://japanese-addresses-v2.geoloniamaps.com/api/ja", "http://127.0.0.2/api/ja"):
        monkeypatch.setenv("JP_ADDRESS_BASE_URL", bad)
        got = json.loads(address.address_split({"address": "東京都"}))
        assert got["message"] == address.MSG_URL
    assert len(seen) == 2
    monkeypatch.setenv("JP_ADDRESS_BASE_URL", "http://127.0.0.1:9/api/ja")
    before = len(seen)
    json.loads(address.address_split({"address": "東京都"}))
    assert seen[before].startswith("http://127.0.0.1:9/api/ja.json")
    assert list(tmp_path.iterdir()) == []


def test_oversize_is_not_parsed_as_towns():
    pad = "a" * (address.LIMIT + 1)
    huge = _b({"data": [{"pref": "東京都", "cities": [{"city": "千代田区"}], "pad": pad}]})
    assert len(huge) > address.LIMIT
    calls = []

    def fetch(url):
        calls.append(url)
        return (200, huge)

    got = address.split_address("東京都千代田区", base=BASE, fetch=fetch)
    assert got["status"] == "upstream" and "level" not in got and len(calls) == 1


def test_deeply_nested_json_is_upstream_not_a_crash():
    depth = 200_000
    nested = ("[" * depth) + ("]" * depth)
    body = b'{"data": ' + nested.encode() + b"}"
    assert len(body) < address.LIMIT
    deep_list, calls = _run("東京都千代田区", extra_routes={address.list_url(BASE): (200, body)})
    assert deep_list["status"] == "upstream" and "level" not in deep_list and len(calls) == 1
    deep_town, calls = _run("東京都千代田区霞が関2-1-2", extra_routes={
        address.town_url(BASE, "東京都", "千代田区"): (200, body),
    })
    assert deep_town["status"] == "upstream" and "level" not in deep_town and len(calls) == 2
    assert deep_town["attribution"] == address.ATTRIBUTION


def test_read_body_caps_and_encodings():
    class FP:
        def __init__(self, data):
            self.data = data

        def read(self, n):
            if not self.data:
                return b""
            chunk, self.data = self.data[:n], self.data[n:]
            return chunk

    class Boom:
        def read(self, _n):
            raise AssertionError("read")

    exact = b"a" * address.LIMIT
    assert address.read_body(200, {}, FP(exact)) == exact
    try:
        address.read_body(200, {}, FP(b"a" * (address.LIMIT + 1)))
    except address.TransportError as exc:
        assert exc.status == 200
    else:
        raise AssertionError("cap")
    try:
        address.read_body(200, {"Content-Length": str(address.LIMIT + 1)}, Boom())
    except address.TransportError:
        pass
    else:
        raise AssertionError("content-length")
    import gzip
    payload = b'{"data":[]}'
    unzipped = address.read_body(200, {"Content-Encoding": "gzip"}, FP(gzip.compress(payload)))
    assert unzipped == payload
    bomb = gzip.compress(b"a" * (address.LIMIT + 1))
    try:
        address.read_body(200, {"Content-Encoding": "gzip"}, FP(bomb))
    except address.TransportError as exc:
        assert exc.status == 200
    else:
        raise AssertionError("bomb")
    try:
        address.read_body(200, {"Content-Encoding": "br"}, FP(b"abc"))
    except address.TransportError as exc:
        assert exc.status == 200
    else:
        raise AssertionError("br")


def test_retry_is_one_request():
    calls = []

    def fetch(url):
        calls.append(url)
        raise address.TransportError(None)

    got = address.split_address("東京都", base=BASE, fetch=fetch)
    assert got["message"] == address.MSG_UPSTREAM and "HTTP" not in got["message"]
    assert len(calls) == 1 and "level" not in got


def test_hyphen_after_kanji_town():
    got, _ = _run("東京都千代田区霞が関二丁目-1-2")
    assert got["town"] == "霞が関二丁目" and got["other"] == "1-2"


def test_no_point_town_uses_city_not_zero():
    got, _ = _run("東京都千代田区猿楽町一丁目1")
    assert got["level"] == 3 and got["town"] == "猿楽町一丁目"
    assert got["point"]["level"] == 2 and got["point"]["lat"] == 35.694003
    assert got["point"]["lat"] != 0
