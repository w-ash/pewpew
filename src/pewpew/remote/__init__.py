"""Connect to a running engine over its preview socket, as the page does.

`client` reads the wire (web/src/wire/protocol.ts types it),
`observe` watches an engine without changing it (tier 0, CLAUDE.md T-7),
and `control` changes the look of an engine on this machine (tier 1).
"""
