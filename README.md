# jp-address

Splits one Japanese address into prefecture, city, town and the remainder, using Geolonia's address data.

The product name is `jp-address`. The only tool is `address_split`. The toolset is `jp_address`. There is no slash command, no CLI, and no cron job. The plugin does not register a hook.

`manifest_version` is 2. `requires_hermes` is `>=0.21.4`. The version is 0.1.0. The license is MIT. Dependencies are the Python standard library only. There is no NOTICE file. Upstream MIT scripts are not included. Logos are not used.

## Tool

`address_split` takes one argument, `address`. Any other argument is rejected before HTTP, with the message `address_split takes only an address string.`

`address` must be a string of 400 characters or fewer. The length is the Python length before normalization. A non-string, or a longer string, is rejected before normalization and before HTTP, with the message `The address must be a string of 400 characters or fewer.`

Normalization is Unicode NFKC, then removal of every character that Python's `str.isspace()` accepts. That includes the space U+0020, the ideographic space U+3000, the tab, the carriage return, the line feed, and rarer separators such as U+2028. Nothing that is not whitespace is removed. The minus sign U+2212 is not whitespace and is not an ASCII hyphen either, so `霞が関２−１−２` written with U+2212 stays level 2, while the fullwidth hyphen-minus U+FF0D becomes `-` under NFKC and behaves like `-`. Town-file names get that same normalization before they are compared. The town name in a result stays the spelling in the file. A compatibility character such as `塚` matches `塚`. `澤` does not match `沢`, and `舘` does not match `館`. `ヶ` and `ケ` are not folded. A separate old-kanji dictionary is not applied. A list row that has a county matches both with that county and without it. A county that is not on the row is not inserted. A Kyoto street name is not deleted. `番地` and `号` are not rewritten to hyphens. A romanized `pref_r` value is not used as a name.

An address that is empty after that removal is level 0. `other` is empty. No HTTP request is sent. `東京都\n千代田区\n霞が関2-1-2` is the same as `東京都千代田区霞が関2-1-2`.

Levels are 0, 1, 2, and 3 only. Level 8 is not returned. Block and lot files are not fetched. A success result does not include `csv_ranges`, `rsdt`, or `machiaza_id`.

`other` is the unmatched remainder. A level 3 remainder that starts with one ASCII hyphen loses that one character. `霞が関二丁目-1-2` therefore has `other` `1-2`.

## Result

| Level | Meaning |
|---|---|
| 0 | No prefecture and no single municipality. Success, not an upstream failure. |
| 1 | The prefecture matched and the municipality did not. Other prefectures are not searched. `東京都大阪市` stays level 1. |
| 2 | The municipality matched and no single town matched. |
| 3 | One town matched. |

The source lists longitude first; results name lat and lng. When the source file has `point` as `[longitude, latitude]`, the result names `lat` and `lng` in that swapped order. A town point uses point level 3. If the town has no point, the municipality point is used and the point level is 2, while the address level stays 3. If that is also missing, the prefecture point is used and the point level is 1. If none of those points exist, the result has no `point` key. A pair outside latitude -90 to 90 or longitude -180 to 180 is treated as missing. Coordinates are not invented. A point can be coarser than the town. It is not a rooftop geocode.

`東京都千代田区霞が関2-1-2`, `東京都千代田区霞が関二丁目1-2`, and `東京都千代田区霞が関2丁目1-2` are the same town when the town row is `霞が関` plus `二丁目` with `chome_n` 2 and point `[139.750413, 35.675551]`. The result is prefecture `東京都`, city `千代田区`, town `霞が関二丁目`, `other` `1-2`, level 3, `lat` 35.675551, `lng` 139.750413, point level 3.

`東京都千代田区霞が関` does not match a town named `霞が関二丁目`. It is level 2, `other` is `霞が関`, and the point is the municipality point at point level 2. It does not pick 一丁目.

`霞が関21-2` does not match 二丁目. An Arabic chome is used only when `chome_n` is an integer from 1 to 99 and not a boolean. When every row for that oaza has a chome, the accepted prefixes are the oaza plus those digits plus `丁目`, the oaza plus those digits plus `-`, and the oaza plus those digits only when the next character is the end, `番`, `号`, `-`, or a kanji numeral. `霞が関2-1-2` still matches 二丁目, because that oaza has no row without a chome. When the same town file also holds a row that has no `chome` and whose own name is exactly that oaza, an Arabic number after the name does not select the chome. That applies when the number is followed by the end of the address, `-`, `番` (and therefore `番地`), `号`, or a kanji numeral. The result is `ambiguous_town`: `宮ケ丘3番地1`, `宮ケ丘3-1`, and `宮ケ丘3号` all list the no-chome row and the chome row. The row with no `chome` may be a `koaza`-only row. 仙台市青葉区 has the koaza `中山` and the oaza `中山` with `一丁目`, so `宮城県仙台市青葉区中山1`, `中山1-2`, and `中山1番地` are `ambiguous_town` and do not become `中山一丁目`. Only a written `丁目`, in Arabic digits or in kanji, selects the chome: `宮ケ丘3丁目`, `宮ケ丘三丁目`, `中山1丁目`, and `中山一丁目`. The `machiaza_id` values are rows that match a prefix of the input. A koaza that shares the oaza and does not match that prefix is not included. A row with no `chome_n` matches the kanji name only. `2丁目` is read as that kanji name, so it still matches when `chome_n` is missing, a boolean, or a decimal. The hyphen form and a bare digit still need an integer `chome_n`. A decimal `chome_n` is not used for those forms. `ヶ` in `宮ヶ丘` does not match `宮ケ丘`. If two normalized names match at the same length, the result is `ambiguous_town`, message `More than one town matches the same span.` If the matched lengths differ, the message is `More than one town matches this address at different lengths.` An `ambiguous_town` result carries `towns`, the names of those rows in file order, beside the matching `machiaza_id` values, so the choice can be put to the person who asked. Fullwidth `内郷御厩町１丁目` matches both the residential `一丁目` row and the koaza `１丁目`.

A row with no `oaza_cho` and a `koaza` uses the koaza as the town name. `東京都千代田区四谷見付` is town `四谷見付`, level 3. The sample point `[139.730722, 35.687428]` is `lat` 35.687428 and `lng` 139.730722. When a row has both `oaza_cho` and `koaza`, the town name is the oaza, then the chome, then the koaza. `大字泊村字メノコ走` matches that longer row. `大字泊村` alone is level 2 when the same file has a longer name and the address matches none of those longer names. The same address is level 3 when the file has only that oaza row. `大字泊村字糸泊` is level 2 because `字糸泊山ノ上` is longer and was not written. `大字泊村字糸泊山ノ上` stays level 3.

The longest town prefix wins. A shorter row named `霞が関` does not beat `霞が関二丁目`. A match is kept only when the next character is a digit, a kanji numeral (`〇零一二三四五六七八九十百千`), `番` (and therefore `番地`), `号`, `-`, `字`, `丁`, or the end of the address. `岩手県盛岡市舘向町1-1` does not become the one-character town `舘`. It stays level 2. `宮城県仙台市青葉区宮城町1` does not become the town `宮`. `東京都千代田区丸の内一丁目一番一号`, `青森県青森市沖館三丁目一番一号`, and `岩手県盛岡市大塚三番地` stay level 3 on those towns. Two rows with the same match length are `ambiguous_town`, message `More than one town matches the same span.` Rows that match at different lengths, such as `岩手県盛岡市門2-3`, use `More than one town matches this address at different lengths.` The `machiaza_id` values are returned. Neither point is used, and the result is not a level 3 success.

Before comparing, an ASCII digit run immediately before `条`, `線`, `号`, `地割`, `丁目`, or `番町` is also read as a kanji numeral from 0 through 99. `0` is `零`. `10` is `十`, `11` is `十一`, `20` is `二十`, and `21` is `二十一`. A number above 99 is left as digits. The reading is applied to the input only, and the consumed length is an index into the original string. The stored town name is not rewritten. Digits before a hyphen stay digits, so `霞が関21-2` still does not match 二丁目. `区` is not one of those suffixes.

A matched town X is not a level 3 result when the same file contains a longer name that starts with X and the address matches none of those longer names. The result is level 2, with the municipality point, unless another safe town still makes the result `ambiguous_town`. A correct address that really names the shorter town also stays at level 2. A coarser correct answer is safer than a wrong success. How often that happens depends on the municipality. Feeding each row's own town name back in, level 3 came out for 124 of 124 rows in 千代田区, 1055 of 1058 in 札幌市北区, 2700 of 2733 in 旭川市, 5645 of 5987 in いわき市, and 1468 of 1788 in 盛岡市 (228 of the rest are `ambiguous_town`). 京都市中京区 is the outlier at 1741 of 3480, because rows such as `上本能寺前町` share a prefix with longer rows such as `上本能寺前町御池通寺町`: in that ward about half of the town names need their street part written out to reach level 3. Those twelve files are the ones measured; the other 1886 municipalities were not. `北海道札幌市中央区宮の森1条1丁目1` is level 3, town `宮の森一条一丁目`. Bare `宮の森` is level 2. `北海道帯広市岩内町1線1` is level 3, town `岩内町一線`. `北海道帯広市以平町西10線1` and `北海道帯広市別府町南13線1` stay level 2, because `以平町西十線中` and `別府町南十三線西` are longer and were not matched. `北海道帯広市緑ケ丘1条1丁目1` stays level 2, because the town is `緑ケ丘一条通一丁目` and the input omits `通`. `北海道帯広市緑ケ丘1条通1丁目1` is level 3. `北海道旭川市春光町1区1` stays level 2. `春光町一区一条1` is level 3. A town-file element that is not an object fails the whole file as `upstream`. An empty town array is still level 2.

If the prefecture is omitted and exactly one municipality name matches, that prefecture is used and the town file is fetched. `千代田区霞が関2-1-2` is level 3 when only one `千代田区` is in the list. Zero matches, including a foreign address such as `1600 Pennsylvania`, are level 0 after the list GET only. They are not an upstream error.

If the prefecture is omitted and the same municipality name is in two or more prefectures, the status is `ambiguous_city` and the message is `This municipality name is in more than one prefecture. Include the prefecture.` The prefecture names are returned. The town file is not fetched. The list GET is the only request.

If two or more rows in one prefecture share the matched name, the status is also `ambiguous_city`, even when the points are equal. The message is `This name matches more than one municipality. Include the county.` The `municipalities` array lists each official name in list order. No point is returned, and the town file is not fetched. This is not the prefecture message above: both rows can be in the same prefecture. `北海道泊村` matches `古宇郡泊村` and `国後郡泊村` when both rows are in the list. `北海道古宇郡泊村` matches only the longer name.

`city` in a level 2 or 3 result is the list's county, city, and ward joined, skipping an empty county or ward. `other` starts after the prefix that matched, which may be the shorter name without the county. `長野県軽井沢町` and `長野県北佐久郡軽井沢町` both use city `北佐久郡軽井沢町` when the list row has county `北佐久郡`.

## Network

The default base is the list URL with the final `.json` removed. The list URL is `https://japanese-addresses-v2.geoloniamaps.com/api/ja.json`. Set `JP_ADDRESS_BASE_URL` to replace the base. The value may contain only a scheme, a host, an optional port, and a path. A query, a fragment, userinfo, an empty string, or a trailing slash is rejected before HTTP, with the message `JP_ADDRESS_BASE_URL is not a usable origin.`

Plain http is accepted only for `127.0.0.1` and `localhost`. Any other http host, including the public host, is rejected before a connection. On 2026-10-08 the public host answered plain http with HTTP 200 and no redirect. This plugin does not use that response.

One call sends at most two GET requests. There is no daily limit. There is no POST. The first GET is `{base}.json`. The second GET is sent only after one municipality is chosen: `{base}/{prefecture}/{municipality}.json`. Each segment is UTF-8 percent-encoded. The municipality file name is the list's `county`, `city`, and `ward` joined, skipping a missing or empty county or ward. `軽井沢町` with county `北佐久郡` is `北佐久郡軽井沢町.json`. `札幌市` with ward `中央区` and no county is `札幌市中央区.json`, not `札幌市.json`. The house number, lot, and building name are not put in the URL.

`GEOLONIA_API_KEY` is not read. The query `geolonia-api-key` is not added. A key is not written into the URL, the result, or an error.

301, 302, 303, 307, and 308 are not followed. The `Location` host is not requested. The redirect body is not used as a split.

Each socket operation waits up to 30 seconds, and reading the response body stops at the first socket read that ends after 30 seconds from the start of the request, so a body can take a little under 60 seconds. That body deadline does not cover connecting or reading the response headers, so a host that sends its headers very slowly can hold a GET longer; only the host you are talking to can do that. There is no limit on a whole call. A body that arrives in a slow trickle is `upstream`, not a successful split. There is no retry, including after a 5xx response. There is no sleep between the two GETs. Nothing is cached in memory or on disk. The plugin does not create `plugin-data/jp-address`.

A raw body, and a gzip body after decompression, must be 8_000_000 bytes or fewer. A larger body is not parsed as a town list. `Content-Encoding: gzip` is the only compression that is decoded. Any other content encoding fails.

HTTP that is not 200 is `upstream`. A 200 body that is not a JSON object, or whose `data` is not an array, is `upstream`. A body whose arrays nest deeper than the interpreter's recursion limit is also `upstream`; the `RecursionError` does not reach the caller. An empty 200, an HTML 200, `{"error":"no"}`, and `{"meta":{}}` are not level 0. A town file whose `data` is `[]` is a real level 2 result, not a failure. After the municipality has matched, a town-file failure (timeout, 5xx, or broken JSON) is `upstream` and is not returned as a finished level 2. A list-file failure is not returned as level 0. The message is `The address file could not be read.` The HTTP status digits are added when the status is known. HTML, `NoSuchKey`, and a script URL are not copied into the result.

`rsdt` and `csv_ranges` do not cause a third GET. `.txt` files are not requested.

## Who can call it

Hermes turns this tool on for every surface, including the gateway, until you turn a surface off with `hermes tools`. The plugin has no user list of its own. Anyone you allow on a gateway can call the tool. It does not ask for approval. Cron, yolo, approvals off, and an unattended session still send the GET when the tool runs. This plugin creates no cron job. It has no slash command for `hermes tools` to stop.

## Attribution

Every result, including a failure, has this `attribution` value:

Geolonia 住所データ（CC BY 4.0 https://creativecommons.org/licenses/by/4.0/）。本データは、「アドレス・ベース・レジストリ」（デジタル庁）をもとに株式会社 Geolonia が作成したものです。「アドレス・ベース・レジストリ」（デジタル庁）（https://dataset.address-br.digital.go.jp）をもとに株式会社 Geolonia が作成し、jp-address が町丁目までを選択した。

Geolonia address data is under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/legalcode.ja). The deed page is not the license. The address base registry uses the Japanese public data license 1.0 (https://www.digital.go.jp/resources/open_data/public_data_license_v1.0). The registry terms are https://www.digital.go.jp/policies/base_registry_address_tos . The dataset page is https://dataset.address-br.digital.go.jp . The publisher's README is https://github.com/geolonia/japanese-addresses-v2/blob/main/README.md .

The publisher says:

現在、制限無しで無料公開をしていますが、様子を見ながら公開の停止や変更などを行うことがあります。商用稼働は、ご自身でデータを作成しホスティングすることを強くおすすめします。

Geolonia では有償で管理・ホスティングするサービスがありますので、ご利用の方はお問い合わせください。

That paid hosting service is not a feature of this plugin.

Messages from this plugin are English. The Japanese attribution follows them.

## What was measured on 2026-10-08

These calls were made to the public host, outside this plugin:

- The list file was HTTP 200, 314034 bytes, 47 prefectures. The Tokyo point in that file is `[139.691717, 35.689568]`. Chiyoda is city `千代田区` with no ward, and its point is `[139.753634, 35.694003]`.
- The Chiyoda town file was HTTP 200 and 124 rows. `霞が関二丁目` has `chome_n` 2 and point `[139.750413, 35.675551]`.
- A missing list name was HTTP 404 HTML.
- Plain http to the public host was HTTP 200 with no `Location` header.
- `北海道/札幌市中央区.json` was HTTP 200. `北海道/札幌市.json` was HTTP 404 HTML.

On 2026-10-09, outside a Hermes model, these calls were sent at least one second apart:

- The list had 1898 municipality rows. 923 of them had a non-empty `county`. `長野県` / `軽井沢町` has county `北佐久郡`.
- `長野県軽井沢町` and `長野県北佐久郡軽井沢町` were both level 2, city `北佐久郡軽井沢町`, through `長野県/北佐久郡軽井沢町.json` (HTTP 200). The municipality point is `lat` 36.34831, `lng` 138.596966, point level 2. The input had no town name, so the result stopped at level 2.
- `北海道古宇郡泊村` was level 2, city `古宇郡泊村`, through `北海道/古宇郡泊村.json` (HTTP 200). The municipality point is `lat` 43.063212, `lng` 140.498857, point level 2.
- `北海道泊村` was `ambiguous_city`, municipalities `古宇郡泊村` and `国後郡泊村`, after the list GET only. It had no point.
- `札幌市中央区` has `宮ケ丘` with no chome (`machiaza_id` `0075000`) and `宮ケ丘三丁目` (`0075003`, `chome_n` 3). `宮ケ丘3番地1` and `宮ケ丘3-1` were `ambiguous_town` with those two ids and no point. `宮ケ丘3丁目` was level 3, town `宮ケ丘三丁目`, `lat` 43.057254, `lng` 141.309325, point level 3. `宮ヶ丘3番地1` stayed level 2.
- `長野県軽井澤町` stayed level 1. `澤` was not folded to `沢`.
- `東京都千代田区霞が関2-1-2` was still level 3, town `霞が関二丁目`, `other` `1-2`, `lat` 35.675551, `lng` 139.750413.
- The same day, the list and `北海道/古宇郡泊村.json` were fetched again, with at least one second between those two GETs. Before the sibling rule, `北海道古宇郡泊村大字泊村` was level 3, town `大字泊村`, point `lat` 43.093158, `lng` 140.509332, point level 3. That row has this oaza and no koaza. `北海道古宇郡泊村大字泊村字メノコ走` was level 3, town `大字泊村字メノコ走`. That row has no point, so the result uses the municipality point at point level 2. Before the sibling rule, `大字泊村字糸泊` matched town `大字泊村字糸泊`, and `大字泊村字糸泊山ノ上` matched town `大字泊村字糸泊山ノ上`. Those two strings were split against the same response. The current matcher still returns level 3 for `大字泊村字メノコ走` and `大字泊村字糸泊山ノ上`. It returns level 2 for `大字泊村`, `大字泊村1-2`, and `大字泊村字糸泊`.

Later on 2026-10-09, outside a Hermes model, the list and four town files were fetched at least one second apart: `青森県/青森市.json` (HTTP 200, 926 rows), `岩手県/盛岡市.json` (HTTP 200, 1788 rows), `宮城県/仙台市青葉区.json` (HTTP 200, 1024 rows), and `福島県/いわき市.json` (HTTP 200, 5988 rows). The list was HTTP 200 and 314034 bytes. The addresses below were split against those saved responses.

- `岩手県盛岡市舘向町1-1` was level 2, city `盛岡市`, `other` `舘向町1-1`. The municipality point is `lat` 39.701795, `lng` 141.154183, point level 2. The one-character koaza `舘` (`machiaza_id` `0000159`) was not selected. `岩手県盛岡市館向町1-1` was level 3, town `館向町`, `other` `1-1`, `lat` 39.719955, `lng` 141.129598, point level 3 (`0146000`).
- `岩手県盛岡市飯岡新田１地割` and `岩手県盛岡市飯岡新田1地割` were level 3, town `飯岡新田１地割`. That row (`0007101`) has no point, so the result uses the municipality point at point level 2. `岩手県盛岡市飯岡新田１０地割` and `岩手県盛岡市飯岡新田10地割` were level 3, town `飯岡新田１０地割` (`0007102`), also with the municipality point.
- `岩手県盛岡市門2-3` was `ambiguous_town` with `machiaza_id` `0034000` and `0034002` only. The matcher at that time used `More than one town matches the same span.` The current message, because the lengths differ, is `More than one town matches this address at different lengths.`
- `岩手県盛岡市大塚` was level 3, town `大塚` (koaza `0000355`), `lat` 39.713869, `lng` 141.174844, point level 3.
- `宮城県仙台市青葉区宮城町1` was level 2, city `仙台市青葉区`, `other` `宮城町1`. The ward point is `lat` 38.269087, `lng` 140.870378, point level 2. The koaza `宮` was not selected.
- `福島県いわき市内郷御厩町１丁目` and `福島県いわき市内郷御厩町1丁目` were `ambiguous_town` with `machiaza_id` `0041001` and `0041101`. `福島県いわき市内郷御厩町一丁目` was level 3, town `内郷御厩町一丁目`, `lat` 37.044585, `lng` 140.867936, point level 3. `福島県いわき市内郷御厩町1-1` was `ambiguous_town` with `machiaza_id` `0041000` and `0041001` only.
- `青森県青森市沖館3-1-1` was level 3, town `沖館三丁目`, `other` `1-1`, `lat` 40.83742, `lng` 140.722882, point level 3. The result had no `machiaza_id`.

The redirect checks in `tests/test_http_server.py` start `http.server` on `127.0.0.1`. They are skipped when opening a socket is blocked. The other checks use fixtures and do not open a socket.

Also on 2026-10-09, outside a Hermes model, `北海道/帯広市.json` (HTTP 200, 407470 bytes, 1712 rows), `北海道/旭川市.json` (HTTP 200, 672006 bytes, 2733 rows), and `北海道/札幌市北区.json` (HTTP 200, 308235 bytes, 1058 rows) were fetched at least one second apart. Eleven saved town files were then counted for a row with no `chome` whose name is exactly the oaza of a row with a `chome`. There are 51 such groups and 216 such row pairs: 青森市 10 groups, 盛岡市 12, 仙台市青葉区 4, いわき市 18, 札幌市中央区 2, 帯広市 1, 旭川市 4, and 千代田区, 札幌市北区, 北佐久郡軽井沢町, 古宇郡泊村 0 each. It is not a national count. Thirteen of the 51 groups have a `koaza`-only row as the row with no `chome`, including 青森市 栄町 and 浜田 and 仙台市青葉区 栗生 and 中山. Each group was split with `X1`, `X1-2`, `X1番地`, and `X1丁目` against those saved files. No form returned a chome as a level 3 success except `X1丁目`, and `X1丁目` returned level 2 for 帯広市 緑ケ丘 and 旭川市 永山町, whose files start at `七丁目` and `二丁目`. Before this rule the same replay returned a level 3 chome for 54 of those inputs.

The 34 Hokkaido types in 札幌市中央区, 札幌市北区, 帯広市, and 旭川市 were split again against those saved files. No further GET was sent for that replay. Thirty of them are level 3 on the longer town. `以平町西10線1`, `別府町南13線1`, `緑ケ丘1条1丁目1`, and `春光町1区1` are level 2. Outside Hokkaido, the same saved files were counted for a short name that has a longer name in the same file. The six files are 千代田区 (0 groups, 0 pairs), 青森市 (110, 526), 盛岡市 (89, 1244), 仙台市青葉区 (89, 853), いわき市 (336, 7346), and 北佐久郡軽井沢町 (1, 1). That is 625 groups and 9970 pairs. It is not a national count. 泊村 is in Hokkaido and is not in those six. The national town-master zip was not readable from this network, and the 2024 Geolonia archive was not downloaded.

## What was not checked

- `address_split` was not called from a Hermes model.
- Full agreement with `@geolonia/normalize-japanese-addresses` was not tested. A listed county is matched with or without the county in the input. A county that is not on the row is not added. Kyoto street deletion is not implemented. `澤` and `沢` are not folded. `舘` and `館` are not folded. `ヶ` and `ケ` are not folded. NFKC still folds compatibility kanji and fullwidth digits on both the input and the town-file name.
- How many prefectures share one municipality name in the public list is not a claim of this plugin. `ambiguous_city` is tested with a fixture.
- Block and lot `.txt` files are not fetched. The registry map terms were not opened.
- Geolonia's privacy policy was not read in full. A URL path contains only a matched prefecture name and municipality name.
- This README does not say when the public host will stop.

This is not a port of normalize-japanese-addresses.
