# TR-181 Data Model Visualizer

A collection of Python CLI tools that parse TR-181 style `Device.*=value` dumps and produce text-based diagrams for different data model objects.

## Requirements

- Python 3 (no external dependencies)

## Scripts

| Script | Object | Description |
|---|---|---|
| `show_logical_stack.py` | `Device.Logical` | Interface stack tree via recursive `LowerLayers` walk, WAN/LAN role detection |
| `show_firewall_rules.py` | `Device.Firewall` | Chain/rule tables, Level→Policy→Chain resolution, target/protocol display |
| `show_wan_manager.py` | `Device.X_PRPLWARE-COM_WANManager` | WAN modes, per-mode interfaces, IPv4/IPv6 mode, alias-resolved references |

## Usage

```bash
python3 show_logical_stack.py [DM.txt]
python3 show_firewall_rules.py [DM.txt]
python3 show_wan_manager.py [DM.txt]
```

If no file is provided, `DM.txt` in the current directory is used.

## Demo Data

Sample dump files are provided under `demo_dm_data/`:

| File | Description |
|---|---|
| `no-wan-DM.txt` | Device dump without active WAN connection |
| `pon-wan-DM.txt` | Device dump with PON WAN connection |

```bash
python3 show_firewall_rules.py demo_dm_data/pon-wan-DM.txt
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
