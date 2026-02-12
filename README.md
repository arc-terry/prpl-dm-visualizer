# TR-181 Data Model Visualizer

A collection of Python CLI tools that parse TR-181 style `Device.*=value` dumps and produce text-based diagrams for different data model objects.

## Requirements

- Python 3 (no external dependencies)

## Scripts

Scripts live under `dm_visualizers/`:

| Script | Object | Description |
|---|---|---|
| `dm_visualizers/show_logical_stack.py` | `Device.Logical` | Interface stack tree via recursive `LowerLayers` walk, WAN/LAN role detection |
| `dm_visualizers/show_firewall_rules.py` | `Device.Firewall` | Chain/rule tables, Level→Policy→Chain resolution, target/protocol display |
| `dm_visualizers/show_wan_manager.py` | `Device.X_PRPLWARE-COM_WANManager` | WAN modes, per-mode interfaces, IPv4/IPv6 mode, alias-resolved references |

## Usage

```bash
python3 visualize.py
python3 visualize.py show_firewall_rules demo_dm_data/pon-wan-DM.txt

python3 dm_visualizers/show_logical_stack.py [DM.txt]
python3 dm_visualizers/show_firewall_rules.py [DM.txt]
python3 dm_visualizers/show_wan_manager.py [DM.txt]
```

`visualize.py` prompts you to choose a visualizer when you omit the script name.
You can enter a number or a unique name prefix (auto-completed when unambiguous).
If no file is provided, it prompts for a DM file (defaulting to `DM.txt` when present).
The DM file prompt supports tab completion on systems with Python readline, including subdirectories like `demo_dm_data/`.

## Adding a New Visualizer

1. Add a new script under `dm_visualizers/` (for example: `dm_visualizers/show_qos.py`).
2. Keep a `Usage:` line in the module docstring for consistency.
3. Run `python3 visualize.py` — the controller auto-detects new scripts.

## Demo Data

Sample dump files are provided under `demo_dm_data/`:

| File | Description |
|---|---|
| `no-wan-DM.txt` | Device dump without active WAN connection |
| `pon-wan-DM.txt` | Device dump with PON WAN connection |

```bash
python3 dm_visualizers/show_firewall_rules.py demo_dm_data/pon-wan-DM.txt
```

## Input Format

The input file should contain lines like:

```
Device.Logical.Interface.1.Name="wan"
Device.Firewall.Chain.1.Rule.2.DestPort=53
Device.X_PRPLWARE-COM_WANManager.WAN.1.Intf.1.IPv4Mode="dhcp4"
```

Only `Device.*=value` lines are parsed; object header lines like `Device.Bridging.` are ignored.

## Adaptive Layout

All scripts auto-detect terminal width and switch between:

- **Compact layout** (< 90 columns) — card-style with stacked details
- **Wide layout** (≥ 90 columns) — tabular with aligned columns

## Documentation

- [`doc/tr181-fw.md`](doc/tr181-fw.md) — TR-181 Firewall object hierarchy and chain selection mechanism

## References

- [Broadband Forum TR-181](https://device-data-model.broadband-forum.org/) — Device:2 Data Model
- [prpl Foundation plugins](https://gitlab.com/prpl-foundation/components/core/plugins/) — TR-181 plugin implementations
