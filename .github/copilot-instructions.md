# Copilot instructions

## Build, test, lint
- Run the controller CLI: `python3 visualize.py [visualizer] [DM.txt]`.
- Run a specific visualizer directly: `python3 dm_visualizers/show_firewall_rules.py [DM.txt]`.
- No automated tests or lint configs are present in this repo.

## High-level architecture
- `visualize.py` discovers and runs `dm_visualizers/show_*.py` scripts.
- Visualizers share helpers in `dm_visualizers/utils.py` for parsing, box drawing, and width-aware padding.
- Logical stack output follows `LowerLayers` references and derives roles from `X_PRPLWARE-COM_WAN.Status` / `X_PRPLWARE-COM_LAN.Status`.

## Key conventions
- Only lines matching `Device.*=...` are parsed; object header lines like `Device.Bridging.` are ignored.
- Object paths may appear with or without a trailing dot; helpers normalize with `rstrip('.')` and try both `obj.attr` and `obj..attr`.
- `LowerLayers` values are comma-separated references; trim whitespace and trailing dots before use.
- Display names prefer `Name`, fall back to `Alias`; role is `WAN`/`LAN` when the vendor status is `Enabled`.
- Visualizer scripts must be named `show_*.py` to be discovered by `visualize.py`.
- Visualizers call `warn_narrow_width()` and emit a warning when width < 80 columns.
