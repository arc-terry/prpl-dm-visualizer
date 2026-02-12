# Copilot instructions

## Build, test, lint
- Run the CLI: `python3 dm_visualizers/show_logical_stack.py [DM.txt]`
- No automated tests or lint configs are present in this repo.

## High-level architecture
- `dm_visualizers/show_logical_stack.py` is a standalone CLI that parses a TR-181 style dump (`DM.txt`) of `Device.*=value` lines into a key/value dict.
- Logical interfaces are discovered via `Device.Logical.Interface.<id>.Name` keys, then their stacks are printed by recursively following `LowerLayers` references.
- Output includes a per-interface tree plus a summary table; interface role is derived from `X_PRPLWARE-COM_WAN.Status` / `X_PRPLWARE-COM_LAN.Status`.

## Key conventions
- Only lines matching `Device.*=...` are parsed; object header lines like `Device.Bridging.` are ignored.
- Object paths may appear with or without a trailing dot; helpers normalize with `rstrip('.')` and try both `obj.attr` and `obj..attr`.
- `LowerLayers` values are comma-separated references; trim whitespace and trailing dots before use.
- Display names prefer `Name`, fall back to `Alias`; role is `WAN`/`LAN` when the vendor status is `Enabled`.
