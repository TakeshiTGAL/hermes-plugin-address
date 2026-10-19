# Changelog

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
