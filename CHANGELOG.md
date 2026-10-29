# Changelog

## 0.1.9

What was understood: company talk treated two katakana characters followed by kanji as a registry name, so フィボナッチ数列 and グラタン皿 received the address paragraph. The agreement test pinned jp-charts at `871f2b9155285e6ea1c3e1fc67b1f76f2c0e4012`, which is not the charts commit beside this checkout. Pytest before this change, on 0.1.8: 53 passed, 2 skipped when that older charts commit was beside this repo, and 1 failed against the later charts commit.

What changed: `pre_llm_call` adds the address paragraph only on an address question (所在地, 住所, 都道府県, 丁目, 番地, a prefecture name, or `address_split` called in the previous turn). A company name does not add it. The decision is `turn_scope.domains`, copied into this plugin and not imported from another. The agreement test pins the jp-charts commit that this revision was checked against. Pytest on this commit: 54 passed, 4 skipped.

## 0.1.8

What was understood: `pre_llm_call` added the address paragraph on every turn, including a settings question. The copy of the chart condition still matched success wording, so it did not follow jp-charts after that plugin stopped replacing replies. A prefecture written in a reply was removed even when `address_split` had not been called. Pytest before this change, on 0.1.7: 52 passed, 2 skipped.

What changed: `pre_llm_call` adds the same paragraph only on company talk or an address question. The copy follows the tool record: jp-charts appends one line when this turn has no figure and an area tool other than `address_split` alone was called, or any tool was called on a company or filing question. This plugin returns no string in that case. When `address_split` was not called, the reply is left as it is. Pytest on this commit: 53 passed, 2 skipped.

## 0.1.7

What was understood: the copy of the chart rewrite condition matched "retrieved successfully" and did not match "successfully retrieved", "has been verified", "has been completed", or "obtained using". An error-only data tool, with no next_step and no 10-digit number, was not a rewrite. No test checked that this copy and jp-charts' public rewrite return a string on opposite sides of one reply. Pytest before this change, on 0.1.6: 51 passed, 2 skipped.

What changed: the copy includes those phrases and the error-only case. When the copy is true, `transform_llm_output` returns no string. The test loads jp-charts at 12dd350d90b92561d59b668e17ab7cd4824cd9ad and calls `rewrite`. Pytest on this commit: 52 passed, 2 skipped.

## 0.1.6

What was understood: `remember` set `split` true when `address_split` was called, including level 0, which returns no `pref`. `correct` then left a prefecture name in the reply. level 0, bad_args, and upstream were not told apart. Pytest before this change, on 0.1.5: 50 passed, 2 skipped.

What changed: a call with no `pref` does not count as a split. A prefecture named in the reply is removed. level 0, bad_args, and upstream each say the address was not split. Pytest on this commit: 51 passed, 2 skipped.

## 0.1.5

What was understood: `pre_llm_call` told the model not to split an address when no tool result contained one, and it did not read tool results. When the chart reply was left as written, this plugin could not correct a sentence that denied a prefecture `address_split` had returned. Pytest on this commit: 50 passed, 2 skipped.

What changed: `transform_tool_result` remembers `pref`, `address`, and `location` and returns no string. `pre_llm_call` copies a returned prefecture and, when none was returned, still says the address was not split and names `absent` by level. `transform_llm_output` replaces only the contradicting address sentence, and only when the reply would otherwise stay. A missing part is not written as 0. `address_split` is not blocked.

## 0.1.4

What was understood: `address_split` already returns `absent` by level. On a small model no address string was in a tool result, so `address_split` was not called, and the reply said the registered address could be confirmed. The user was not told that the address was not split, or which parts `absent` lists. Pytest on this commit: 43 passed, 4 skipped.

What changed: `pre_llm_call` says that when no tool result contains an address, the address was not returned and was not split, and it names `absent` by level (pref, city, and town at level 0; city and town at level 1; town at level 2; none at level 3). A missing part is not written as 0. The tool is not blocked when the user types an address.

## 0.1.3

What was understood: `address_split` already returned prefecture, city, and town, and left a part out when the address data did not contain it. A level below 3 did not name the missing parts, so a caller could not tell an omitted town from a field that was never defined. The previous version's tool diff was the User-Agent string. On a small model the skill body was not opened, `address_split` was not called, and the reply said the address had been confirmed.

What changed: a result that has `level` also has `absent`: level 0 lists pref, city, and town; level 1 lists city and town; level 2 lists town; level 3 lists nothing. A status without `level` (ambiguous, upstream, bad_args) does not gain `absent`. Nothing is written as 0. `pre_llm_call` tells the model to call `address_split` only with an address copied from a tool result, and not to name a prefecture when no tool returned one.

## 0.1.2

What was understood: `address_split` already returns prefecture, city, town, and the remainder, and it leaves a part out when the address data does not contain it. A company sheet was asking the model to paste the registered address as one line.

What changed: the `japanese-address` skill tells the model to pass `jp_corp_profile`'s `location` into `address_split` and to copy only the parts the tool returned, with the attribution. A missing town is not filled with 0.

## 0.1.1

Adds the `japanese-address` skill. It tells the model to find `address_split` with tool_search before web_search. It does not set requires_toolsets, so it stays in the model's skill list when Tool Search is left at its default, which hides this plugin's tools.

What was found: in 18 real sessions with five models (17 answered), one model handled a Fuchu address by calling web search six times and web extract once instead of `address_split`, and two replies left out the attribution.

What changed: the tool description now starts with when to use it, what it returns (including `other` and `attribution`), and that `other` and `attribution` belong in the reply. `JP_ADDRESS_BASE_URL` is now read with `agent.secret_scope.get_secret` on each call instead of `os.environ`, so with more than one profile each profile's own value is used.

After the change, in the same scenarios with the same models: the Fuchu scenario called `address_split`, and no reply that used an `address_split` result left out the attribution. These are small samples.

The first sentence Tool Search shows now uses the words a person would ask with. A sentence that starts by describing the mechanism is not found, and the model falls through to the built-in web_search.

A prefecture written without 都, 府, or 県, and fullwidth digits, are accepted. Extra arguments and an address that is only letters are refused with a fix and an example. Argument errors add `ok: false` and `error_type`.

The plugin description no longer says it was not tested from a Hermes model; it points to the 18 sessions above instead.

## 0.1.0

First release.
