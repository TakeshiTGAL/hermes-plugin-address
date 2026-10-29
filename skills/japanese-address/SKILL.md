---
name: japanese-address
description: "Split a Japanese address into prefecture, city, and town. Before web_search, use tool_search to find address_split and tool_call it only with an address copied from a tool result. If none, say the address was not returned and was not split. absent lists pref, city, and town at level 0; city and town at level 1; town at level 2; none at level 3. Those parts are not 0."
---

For this kind of request, use tool_search to find this plugin's tools before web_search, then call them with tool_call. Write tool_search queries in English (for example: "Japanese address").

Tool: `address_split`. Copy the attribution it returns.

When `jp_corp_profile` returns `location`, call `address_split` on that string. If `address_split` returned `pref`, copy that prefecture and do not say the address is missing. If no tool result contains an address, say the address was not returned and was not split, and do not name a prefecture. Report prefecture, city, town, and `other` only as the tool returned them, plus the attribution URL. `absent` lists pref, city, and town at level 0, city and town at level 1, town at level 2, and nothing at level 3. Do not write 0 for a missing town, chome, or point, and do not invent one. A point can be coarser than the town. Do not treat the split as a rooftop geocode.
