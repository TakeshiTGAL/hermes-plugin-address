"""The 34 Hokkaido types and ten sibling groups outside Hokkaido.

Rows are excerpts of the public town files. Expectations were replayed
against those full files. The tests themselves do not open a socket.
"""

import json

import address

BASE = "https://example.test/api/ja"

OBI = (42.924014, 143.196195)
ASA = (43.771404, 142.365314)
CHUO = (43.061414, 141.35389)
KITA = (43.090693, 141.340882)
AOMORI = (40.822358, 140.74732)
MORIOKA = (39.701795, 141.154183)
SENDAI = (38.269087, 140.870378)
IWAKI = (37.050456, 140.887687)
KARUI = (36.34831, 138.596966)


def _b(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False).encode()


def _run(text, prefs, routes):
    table = {address.list_url(BASE): (200, _b({"data": prefs}))}
    table.update(routes)

    def fetch(url):
        if url not in table:
            return 404, b"missing"
        return table[url]

    return address.split_address(text, base=BASE, fetch=fetch)


def _names(rows):
    found = {}
    for row in rows:
        found[address._town_name(row)] = row
    return found


def _expect(got, city_ll, town, other, by_name):
    assert got["attribution"] == address.ATTRIBUTION
    if town is None:
        assert got["level"] == 2 and "town" not in got and got["other"] == other
        assert got["point"] == {"lat": city_ll[0], "lng": city_ll[1], "level": 2}
        assert "status" not in got and "machiaza_id" not in got
        return
    assert got["level"] == 3 and got["town"] == town and got["other"] == other
    point = by_name[town].get("point")
    if point:
        assert got["point"] == {"lat": point[1], "lng": point[0], "level": 3}
    else:
        assert got["point"] == {"lat": city_ll[0], "lng": city_ll[1], "level": 2}
    assert "machiaza_id" not in got


OBIHIRO_ROWS = [
    {"machiaza_id": "0025000", "oaza_cho": "以平町西", "point": [143.210235, 42.754669]},
    {"machiaza_id": "0026000", "oaza_cho": "以平町西十線", "point": [143.218775, 42.760178]},
    {"machiaza_id": "0376000", "oaza_cho": "以平町西十線中"},
    {"machiaza_id": "0045000", "oaza_cho": "岩内町", "point": [142.865927, 42.717229]},
    {"machiaza_id": "0046000", "oaza_cho": "岩内町一線", "point": [143.011021, 42.651079]},
    {"machiaza_id": "0052000", "oaza_cho": "岩内町西", "point": [143.012645, 42.681515]},
    {"machiaza_id": "0053000", "oaza_cho": "岩内町西一線", "point": [143.03557, 42.674372]},
    {"machiaza_id": "0057000", "oaza_cho": "岩内町東", "point": [143.037365, 42.651465]},
    {"machiaza_id": "0058000", "oaza_cho": "岩内町東一線", "point": [143.058168, 42.683015]},
    {"machiaza_id": "0071000", "oaza_cho": "上帯広町東", "point": [143.076164, 42.794505]},
    {"machiaza_id": "0072000", "oaza_cho": "上帯広町東一線", "point": [143.055464, 42.775273]},
    {"machiaza_id": "0082000", "oaza_cho": "川西町西", "point": [143.158846, 42.861722]},
    {"machiaza_id": "0083000", "oaza_cho": "川西町西一線", "point": [143.177378, 42.851167]},
    {"machiaza_id": "0122000", "oaza_cho": "桜木町東", "point": [143.231799, 42.776858]},
    {"machiaza_id": "0123000", "oaza_cho": "桜木町東一線", "point": [143.207184, 42.80077]},
    {"machiaza_id": "0133000", "oaza_cho": "昭和町西", "point": [143.137305, 42.780742]},
    {"machiaza_id": "0134000", "oaza_cho": "昭和町西一線", "point": [143.148647, 42.778384]},
    {"machiaza_id": "0136000", "oaza_cho": "昭和町東", "point": [143.171103, 42.784797]},
    {"machiaza_id": "0137000", "oaza_cho": "昭和町東一線", "point": [143.159336, 42.770353]},
    {"machiaza_id": "0152000", "oaza_cho": "大正町西", "point": [143.162173, 42.81119]},
    {"machiaza_id": "0153000", "oaza_cho": "大正町西一線", "point": [143.171263, 42.81682300000001]},
    {"machiaza_id": "0154000", "oaza_cho": "大正町東", "point": [143.203859, 42.813832]},
    {"machiaza_id": "0155000", "oaza_cho": "大正町東一線", "point": [143.18515, 42.815332]},
    {"machiaza_id": "0174000", "oaza_cho": "拓成町西", "point": [143.005589, 42.70548]},
    {"machiaza_id": "0175000", "oaza_cho": "拓成町西四線", "point": [143.02992, 42.702315]},
    {"machiaza_id": "0178000", "oaza_cho": "拓成町南", "point": [142.95505, 42.696814]},
    {"machiaza_id": "0179000", "oaza_cho": "拓成町南一線", "point": [142.968606, 42.70078]},
    {"machiaza_id": "0183000", "oaza_cho": "豊西町西", "point": [143.137634, 42.838167]},
    {"machiaza_id": "0184000", "oaza_cho": "豊西町西一線", "point": [143.150794, 42.81725600000001]},
    {"machiaza_id": "0191000", "oaza_cho": "中島町東", "point": [143.146938, 42.728884]},
    {"machiaza_id": "0192000", "oaza_cho": "中島町東三線", "point": [143.124796, 42.747587]},
    {"machiaza_id": "0253000", "oaza_cho": "美栄町西", "point": [143.062667, 42.780924]},
    {"machiaza_id": "0254000", "oaza_cho": "美栄町西三線", "point": [143.083863, 42.756807]},
    {"machiaza_id": "0289000", "oaza_cho": "広野町西", "point": [142.986985, 42.751491]},
    {"machiaza_id": "0290000", "oaza_cho": "広野町西一線", "point": [143.02251, 42.75916]},
    {"machiaza_id": "0296000", "oaza_cho": "広野町東", "point": [143.020599, 42.736562]},
    {"machiaza_id": "0297000", "oaza_cho": "広野町東一線", "point": [143.027959, 42.748888]},
    {"machiaza_id": "0298000", "oaza_cho": "富士町西", "point": [143.115016, 42.783625]},
    {"machiaza_id": "0299000", "oaza_cho": "富士町西一線", "point": [143.130244, 42.792077]},
    {"machiaza_id": "0352000", "oaza_cho": "富士町東", "point": [143.142492, 42.801198]},
    {"machiaza_id": "0361000", "oaza_cho": "富士町東一線", "point": [143.147884, 42.795701]},
    {"machiaza_id": "0311000", "oaza_cho": "別府町南", "point": [143.146651, 42.850953]},
    {"machiaza_id": "0312000", "oaza_cho": "別府町南十三線", "point": [143.146243, 42.870612]},
    {"machiaza_id": "0399000", "oaza_cho": "別府町南十三線西"},
    {"machiaza_id": "0322000", "oaza_cho": "緑ケ丘", "point": [143.186214, 42.904384]},
    {"machiaza_id": "0319001", "oaza_cho": "緑ケ丘一条通", "chome": "一丁目", "chome_n": 1, "point": [143.184066, 42.910525]},
    {"machiaza_id": "0332000", "oaza_cho": "基松町西", "point": [143.090603, 42.826746]},
    {"machiaza_id": "0333000", "oaza_cho": "基松町西一線", "point": [143.103799, 42.83296]},
    {"machiaza_id": "0335000", "oaza_cho": "基松町東", "point": [143.096003, 42.812493]},
    {"machiaza_id": "0336000", "oaza_cho": "基松町東一線", "point": [143.118469, 42.830523]},
    {"machiaza_id": "0339000", "oaza_cho": "八千代町西", "point": [142.971233, 42.735036]},
    {"machiaza_id": "0340000", "oaza_cho": "八千代町西一線", "point": [142.984666, 42.725137]},
    {"machiaza_id": "0346000", "oaza_cho": "八千代町東", "point": [143.003974, 42.71533]},
    {"machiaza_id": "0347000", "oaza_cho": "八千代町東一線", "point": [142.999185, 42.722207]},
]

ASAHIKAWA_ROWS = [
    {"machiaza_id": "0238000", "oaza_cho": "西神楽南", "point": [142.37237400000004, 43.649564]},
    {"machiaza_id": "0239001", "oaza_cho": "西神楽南一条", "chome": "一丁目", "chome_n": 1, "point": [142.39461, 43.683514]},
    {"machiaza_id": "0248000", "oaza_cho": "パルプ町", "point": [142.394196, 43.77874700000001]},
    {"machiaza_id": "0249001", "oaza_cho": "パルプ町一条", "chome": "一丁目", "chome_n": 1, "point": [142.385015, 43.772984]},
    {"machiaza_id": "0000132", "koaza": "流通団地", "point": [142.410406, 43.807764]},
    {"machiaza_id": "0331001", "oaza_cho": "流通団地一条", "chome": "一丁目", "chome_n": 1, "point": [142.39620800000003, 43.792142]},
    {"machiaza_id": "0128000", "oaza_cho": "春光町", "point": [142.365115, 43.794293]},
    {"machiaza_id": "0363000", "oaza_cho": "春光町一区一条"},
]

CHUO_ROWS = [
    {"machiaza_id": "0077000", "oaza_cho": "宮の森", "point": [141.287113, 43.044885]},
    {"machiaza_id": "0078001", "oaza_cho": "宮の森一条", "chome": "一丁目", "chome_n": 1, "point": [141.31302200000002, 43.064416]},
]

KITA_ROWS = [
    {"machiaza_id": "0057000", "oaza_cho": "新川", "point": [141.288901, 43.126961]},
    {"machiaza_id": "0058001", "oaza_cho": "新川一条", "chome": "一丁目", "chome_n": 1, "point": [141.320323, 43.093326]},
    {"machiaza_id": "0116000", "oaza_cho": "西茨戸", "point": [141.342407, 43.154256]},
    {"machiaza_id": "0117001", "oaza_cho": "西茨戸一条", "chome": "一丁目", "chome_n": 1, "point": [141.348184, 43.147722]},
    {"machiaza_id": "0124000", "oaza_cho": "東茨戸", "point": [141.36183, 43.168784]},
    {"machiaza_id": "0125001", "oaza_cho": "東茨戸一条", "chome": "一丁目", "chome_n": 1, "point": [141.354959, 43.161121]},
]

# address, city point, town or None, other
HOKKAIDO_34 = [
    ("北海道帯広市以平町西10線1", OBI, None, "以平町西10線1"),
    ("北海道帯広市岩内町1線1", OBI, "岩内町一線", "1"),
    ("北海道帯広市岩内町西1線1", OBI, "岩内町西一線", "1"),
    ("北海道帯広市岩内町東1線1", OBI, "岩内町東一線", "1"),
    ("北海道帯広市上帯広町東1線1", OBI, "上帯広町東一線", "1"),
    ("北海道帯広市川西町西1線1", OBI, "川西町西一線", "1"),
    ("北海道帯広市桜木町東1線1", OBI, "桜木町東一線", "1"),
    ("北海道帯広市昭和町西1線1", OBI, "昭和町西一線", "1"),
    ("北海道帯広市昭和町東1線1", OBI, "昭和町東一線", "1"),
    ("北海道帯広市大正町西1線1", OBI, "大正町西一線", "1"),
    ("北海道帯広市大正町東1線1", OBI, "大正町東一線", "1"),
    ("北海道帯広市拓成町西4線1", OBI, "拓成町西四線", "1"),
    ("北海道帯広市拓成町南1線1", OBI, "拓成町南一線", "1"),
    ("北海道帯広市豊西町西1線1", OBI, "豊西町西一線", "1"),
    ("北海道帯広市中島町東3線1", OBI, "中島町東三線", "1"),
    ("北海道帯広市美栄町西3線1", OBI, "美栄町西三線", "1"),
    ("北海道帯広市広野町西1線1", OBI, "広野町西一線", "1"),
    ("北海道帯広市広野町東1線1", OBI, "広野町東一線", "1"),
    ("北海道帯広市富士町西1線1", OBI, "富士町西一線", "1"),
    ("北海道帯広市別府町南13線1", OBI, None, "別府町南13線1"),
    ("北海道帯広市緑ケ丘1条1丁目1", OBI, None, "緑ケ丘1条1丁目1"),
    ("北海道帯広市基松町西1線1", OBI, "基松町西一線", "1"),
    ("北海道帯広市基松町東1線1", OBI, "基松町東一線", "1"),
    ("北海道帯広市八千代町西1線1", OBI, "八千代町西一線", "1"),
    ("北海道帯広市八千代町東1線1", OBI, "八千代町東一線", "1"),
    ("北海道帯広市富士町東1線1", OBI, "富士町東一線", "1"),
    ("北海道旭川市西神楽南1条1丁目1", ASA, "西神楽南一条一丁目", "1"),
    ("北海道旭川市パルプ町1条1丁目1", ASA, "パルプ町一条一丁目", "1"),
    ("北海道旭川市流通団地1条1丁目1", ASA, "流通団地一条一丁目", "1"),
    ("北海道旭川市春光町1区1", ASA, None, "春光町1区1"),
    ("北海道札幌市中央区宮の森1条1丁目1", CHUO, "宮の森一条一丁目", "1"),
    ("北海道札幌市北区新川1条1丁目1", KITA, "新川一条一丁目", "1"),
    ("北海道札幌市北区西茨戸1条1丁目1", KITA, "西茨戸一条一丁目", "1"),
    ("北海道札幌市北区東茨戸1条1丁目1", KITA, "東茨戸一条一丁目", "1"),
]


def test_hokkaido_thirty_four_types_do_not_return_the_short_town():
    assert len(HOKKAIDO_34) == 34
    prefs = [{"pref": "北海道", "cities": [
        {"city": "帯広市", "point": [143.196195, 42.924014]},
        {"city": "旭川市", "point": [142.365314, 43.771404]},
        {"city": "札幌市", "ward": "中央区", "point": [141.35389, 43.061414]},
        {"city": "札幌市", "ward": "北区", "point": [141.340882, 43.090693]},
    ]}]
    routes = {
        address.town_url(BASE, "北海道", "帯広市"): (200, _b({"data": OBIHIRO_ROWS})),
        address.town_url(BASE, "北海道", "旭川市"): (200, _b({"data": ASAHIKAWA_ROWS})),
        address.town_url(BASE, "北海道", "札幌市中央区"): (200, _b({"data": CHUO_ROWS})),
        address.town_url(BASE, "北海道", "札幌市北区"): (200, _b({"data": KITA_ROWS})),
    }
    by_name = _names(OBIHIRO_ROWS + ASAHIKAWA_ROWS + CHUO_ROWS + KITA_ROWS)
    for text, city_ll, town, other in HOKKAIDO_34:
        got = _run(text, prefs, routes)
        _expect(got, city_ll, town, other, by_name)
    extras = [
        ("北海道帯広市緑ケ丘1条通1丁目1", OBI, "緑ケ丘一条通一丁目", "1"),
        ("北海道旭川市春光町一区一条1", ASA, "春光町一区一条", "1"),
        ("北海道札幌市中央区宮の森", CHUO, None, "宮の森"),
        ("北海道札幌市中央区宮の森一条一丁目1", CHUO, "宮の森一条一丁目", "1"),
        ("北海道札幌市中央区宮の森１条１丁目１", CHUO, "宮の森一条一丁目", "1"),
        ("北海道帯広市岩内町", OBI, None, "岩内町"),
    ]
    for text, city_ll, town, other in extras:
        _expect(_run(text, prefs, routes), city_ll, town, other, by_name)


def test_ten_sibling_groups_outside_hokkaido():
    prefs = [
        {"pref": "青森県", "cities": [{"city": "青森市", "point": [140.74732, 40.822358]}]},
        {"pref": "岩手県", "cities": [{"city": "盛岡市", "point": [141.154183, 39.701795]}]},
        {"pref": "宮城県", "cities": [{"city": "仙台市", "ward": "青葉区", "point": [140.870378, 38.269087]}]},
        {"pref": "福島県", "cities": [{"city": "いわき市", "point": [140.887687, 37.050456]}]},
        {"pref": "長野県", "cities": [{"city": "軽井沢町", "county": "北佐久郡", "point": [138.596966, 36.34831]}]},
    ]
    aomori = [
        {"machiaza_id": "0150000", "oaza_cho": "原別", "point": [140.813122, 40.837423]},
        {"machiaza_id": "0150001", "oaza_cho": "原別", "chome": "一丁目", "chome_n": 1, "point": [140.801292, 40.838368]},
        {"machiaza_id": "0154000", "oaza_cho": "古館", "point": [140.784279, 40.801743]},
        {"machiaza_id": "0154001", "oaza_cho": "古館", "chome": "一丁目", "chome_n": 1, "point": [140.779545, 40.8048]},
        {"machiaza_id": "0019000", "oaza_cho": "大字大野", "point": [140.73346, 40.803804]},
        {"machiaza_id": "0019101", "oaza_cho": "大字大野", "koaza": "字今井"},
    ]
    morioka = [
        {"machiaza_id": "0228000", "oaza_cho": "三ツ割", "point": [141.16363800000002, 39.738611]},
        {"machiaza_id": "0228001", "oaza_cho": "三ツ割", "chome": "一丁目", "chome_n": 1, "point": [141.155729, 39.716754]},
    ]
    sendai = [
        {"machiaza_id": "0000151", "koaza": "中山", "point": [140.737228, 38.284742]},
        {"machiaza_id": "0053001", "oaza_cho": "中山", "chome": "一丁目", "chome_n": 1, "point": [140.846837, 38.290513]},
        {"machiaza_id": "0000144", "koaza": "大竹", "point": [140.787661, 38.278383]},
        {"machiaza_id": "0000145", "koaza": "大竹原", "point": [140.77674400000004, 38.280106]},
    ]
    iwaki = [
        {"machiaza_id": "0744000", "oaza_cho": "上平", "point": [140.862655, 37.133453]},
        {"machiaza_id": "0745000", "oaza_cho": "上平石", "point": [140.702316, 36.95248]},
        {"machiaza_id": "0953000", "oaza_cho": "中野", "point": [140.703858, 36.962396]},
        {"machiaza_id": "0954000", "oaza_cho": "中野地", "point": [140.894052, 36.960026]},
        {"machiaza_id": "0430000", "oaza_cho": "久保", "point": [140.691676, 36.959311]},
        {"machiaza_id": "0431000", "oaza_cho": "久保田", "point": [140.723688, 37.246524]},
    ]
    karui = [
        {"machiaza_id": "0007000", "oaza_cho": "軽井沢", "point": [138.633606, 36.355523]},
        {"machiaza_id": "0008000", "oaza_cho": "軽井沢東", "point": [138.636743, 36.345901]},
    ]
    routes = {
        address.town_url(BASE, "青森県", "青森市"): (200, _b({"data": aomori})),
        address.town_url(BASE, "岩手県", "盛岡市"): (200, _b({"data": morioka})),
        address.town_url(BASE, "宮城県", "仙台市青葉区"): (200, _b({"data": sendai})),
        address.town_url(BASE, "福島県", "いわき市"): (200, _b({"data": iwaki})),
        address.town_url(BASE, "長野県", "北佐久郡軽井沢町"): (200, _b({"data": karui})),
    }
    by_name = _names(aomori + morioka + sendai + iwaki + karui)
    cases = [
        ("青森県青森市原別1丁目1", AOMORI, "原別一丁目", "1"),
        ("青森県青森市原別", AOMORI, None, "原別"),
        ("岩手県盛岡市三ツ割1丁目1", MORIOKA, "三ツ割一丁目", "1"),
        ("岩手県盛岡市三ツ割", MORIOKA, None, "三ツ割"),
        ("宮城県仙台市青葉区中山1丁目1", SENDAI, "中山一丁目", "1"),
        ("宮城県仙台市青葉区中山", SENDAI, None, "中山"),
        ("宮城県仙台市青葉区大竹原", SENDAI, "大竹原", ""),
        ("宮城県仙台市青葉区大竹", SENDAI, None, "大竹"),
        ("宮城県仙台市青葉区大竹1", SENDAI, None, "大竹1"),
        ("福島県いわき市上平石", IWAKI, "上平石", ""),
        ("福島県いわき市上平", IWAKI, None, "上平"),
        ("福島県いわき市上平1", IWAKI, None, "上平1"),
        ("福島県いわき市中野地", IWAKI, "中野地", ""),
        ("福島県いわき市中野1", IWAKI, None, "中野1"),
        ("福島県いわき市久保田", IWAKI, "久保田", ""),
        ("福島県いわき市久保1", IWAKI, None, "久保1"),
        ("長野県軽井沢町軽井沢東", KARUI, "軽井沢東", ""),
        ("長野県北佐久郡軽井沢町軽井沢", KARUI, None, "軽井沢"),
        ("長野県軽井沢町軽井沢1", KARUI, None, "軽井沢1"),
        ("青森県青森市古館1丁目1", AOMORI, "古館一丁目", "1"),
        ("青森県青森市古館", AOMORI, None, "古館"),
        ("青森県青森市大字大野字今井", AOMORI, "大字大野字今井", ""),
        ("青森県青森市大字大野", AOMORI, None, "大字大野"),
        ("青森県青森市大字大野1", AOMORI, None, "大字大野1"),
    ]
    groups = {"原別", "三ツ割", "中山", "大竹", "上平", "中野", "久保", "軽井沢", "古館", "大字大野"}
    assert len(groups) >= 10
    for text, city_ll, town, other in cases:
        _expect(_run(text, prefs, routes), city_ll, town, other, by_name)
    ambiguous = _run("青森県青森市原別1", prefs, routes)
    assert ambiguous["status"] == "ambiguous_town"
    assert ambiguous["message"] == address.MSG_TOWN_LEN
    assert ambiguous["machiaza_id"] == ["0150000", "0150001"]
    gate = _run("岩手県盛岡市三ツ割1", prefs, routes)
    assert gate["message"] == address.MSG_TOWN_LEN
    assert gate["machiaza_id"] == ["0228000", "0228001"]
    furu = _run("青森県青森市古館1", prefs, routes)
    assert furu["message"] == address.MSG_TOWN_LEN
    assert furu["machiaza_id"] == ["0154000", "0154001"]
    # 中山 is a koaza-only row, 中山一丁目 an oaza row. The name is still the same.
    naka = _run("宮城県仙台市青葉区中山1", prefs, routes)
    assert naka["status"] == "ambiguous_town"
    assert naka["message"] == address.MSG_TOWN_LEN
    assert naka["machiaza_id"] == ["0000151", "0053001"]


def test_a_row_without_chome_blocks_the_chome_for_digits_hyphen_and_banchi():
    """栄町, 浜田 and 栗生 are koaza-only rows whose name repeats as an oaza with 丁目.

    原別 is the same shape with an oaza row. In every group an Arabic number, a
    hyphen or 番地 must stay ambiguous, and a written 丁目 must pick the chome.
    """
    prefs = [
        {"pref": "青森県", "cities": [{"city": "青森市", "point": [140.74732, 40.822358]}]},
        {"pref": "宮城県", "cities": [{"city": "仙台市", "ward": "青葉区", "point": [140.870378, 38.269087]}]},
    ]
    aomori = [
        {"machiaza_id": "0000111", "koaza": "栄町", "point": [140.592417, 40.707208]},
        {"machiaza_id": "0097001", "oaza_cho": "栄町", "chome": "一丁目", "chome_n": 1, "point": [140.765524, 40.824741]},
        {"machiaza_id": "0097002", "oaza_cho": "栄町", "chome": "二丁目", "chome_n": 2, "point": [140.771751, 40.825838]},
        {"machiaza_id": "0000191", "koaza": "浜田", "point": [140.84775, 40.872417]},
        {"machiaza_id": "0147001", "oaza_cho": "浜田", "chome": "一丁目", "chome_n": 1, "point": [140.748267, 40.802409]},
        {"machiaza_id": "0147002", "oaza_cho": "浜田", "chome": "二丁目", "chome_n": 2, "point": [140.752229, 40.802048]},
        {"machiaza_id": "0150000", "oaza_cho": "原別", "point": [140.813122, 40.837423]},
        {"machiaza_id": "0150001", "oaza_cho": "原別", "chome": "一丁目", "chome_n": 1, "point": [140.801292, 40.838368]},
    ]
    sendai = [
        {"machiaza_id": "0000113", "koaza": "栗生", "point": [140.6892, 38.334019]},
        {"machiaza_id": "0048001", "oaza_cho": "栗生", "chome": "一丁目", "chome_n": 1, "point": [140.795574, 38.260969]},
        {"machiaza_id": "0048002", "oaza_cho": "栗生", "chome": "二丁目", "chome_n": 2, "point": [140.79694, 38.267501]},
        {"machiaza_id": "0000151", "koaza": "中山", "point": [140.737228, 38.284742]},
        {"machiaza_id": "0053001", "oaza_cho": "中山", "chome": "一丁目", "chome_n": 1, "point": [140.846837, 38.290513]},
    ]
    routes = {
        address.town_url(BASE, "青森県", "青森市"): (200, _b({"data": aomori})),
        address.town_url(BASE, "宮城県", "仙台市青葉区"): (200, _b({"data": sendai})),
    }
    by_name = _names(aomori + sendai)
    groups = [
        ("青森県青森市", "栄町", AOMORI, ["0000111", "0097001"]),
        ("青森県青森市", "浜田", AOMORI, ["0000191", "0147001"]),
        ("青森県青森市", "原別", AOMORI, ["0150000", "0150001"]),
        ("宮城県仙台市青葉区", "栗生", SENDAI, ["0000113", "0048001"]),
        ("宮城県仙台市青葉区", "中山", SENDAI, ["0000151", "0053001"]),
    ]
    for city, town, city_ll, ids in groups:
        for suffix in ("1", "1-2", "1番地"):
            got = _run(city + town + suffix, prefs, routes)
            assert got["status"] == "ambiguous_town", (city, town, suffix, got)
            assert got["message"] == address.MSG_TOWN_LEN
            assert got["machiaza_id"] == ids
            assert "level" not in got and "point" not in got
        # A kanji lot number is not a chome either. The unmatched 丁目 siblings
        # then keep the bare town at the municipality, as they do without a number.
        _expect(_run(city + town + "一番一号", prefs, routes), city_ll, None, town + "一番一号", by_name)
        for written in ("1丁目2", "一丁目2"):
            _expect(_run(city + town + written, prefs, routes), city_ll, town + "一丁目", "2", by_name)


def test_kanji_reading_of_digits_before_a_suffix():
    prefs = [{"pref": "北海道", "cities": [{"city": "数字市", "point": [141.0, 43.0]}]}]
    rows = [
        {"machiaza_id": "a", "oaza_cho": "甲十一条", "point": [141.1, 43.1]},
        {"machiaza_id": "b", "oaza_cho": "乙二十一条", "point": [141.2, 43.2]},
        {"machiaza_id": "c", "oaza_cho": "丁二十条", "point": [141.3, 43.3]},
        {"machiaza_id": "d", "oaza_cho": "戊", "point": [141.4, 43.4]},
        {"machiaza_id": "e", "oaza_cho": "戊零号", "point": [141.5, 43.5]},
        {"machiaza_id": "f", "oaza_cho": "己百一条"},
    ]
    routes = {address.town_url(BASE, "北海道", "数字市"): (200, _b({"data": rows}))}
    by_name = _names(rows)
    city = (43.0, 141.0)
    _expect(_run("北海道数字市甲11条9", prefs, routes), city, "甲十一条", "9", by_name)
    _expect(_run("北海道数字市乙21条1", prefs, routes), city, "乙二十一条", "1", by_name)
    _expect(_run("北海道数字市丁20条", prefs, routes), city, "丁二十条", "", by_name)
    _expect(_run("北海道数字市戊0号3", prefs, routes), city, "戊零号", "3", by_name)
    _expect(_run("北海道数字市己100条1", prefs, routes), city, None, "己100条1", by_name)
    _expect(_run("北海道数字市甲21条1", prefs, routes), city, None, "甲21条1", by_name)
