---
name: tr181-dm-visualizer
description: 'Generate a Python script that parses a TR-181 DM.txt dump and produces a text-based diagram for a given data model object (e.g. Logical, Firewall, NAT, WiFi, Bridging). Use when user asks to visualize, diagram, or display a TR-181 object from a DM dump file. Supports: (1) Auto-detecting object instances and attributes from DM.txt, (2) Generating adaptive text-based diagrams (compact/wide based on terminal width), (3) Producing per-instance detail views plus summary tables.'
license: MIT
allowed-tools: Bash
---

# TR-181 Data Model Visualizer

## Overview

Generate standalone Python scripts that parse a TR-181 style `Device.*=value` dump file (typically `DM.txt`) and produce text-based diagrams for specific data model objects. Each script follows the established patterns in this repository.

## Background Knowledge

### TR-181 Data Model

TR-181 (Broadband Forum) defines a hierarchical data model for CPE device management. The dump file contains lines like:

```
Device.Firewall.Chain.1.Name="FORWARD_Sentinel"
Device.Firewall.Chain.1.Enable=1
```

Object header lines (no `=`) like `Device.Bridging.` are ignored.

### Key TR-181 Objects and prpl Foundation Plugins

| Object | prpl Plugin | Description |
|---|---|---|
| `Device.Logical` | tr181-logical | Logical network interfaces, LowerLayers stacking |
| `Device.Firewall` | tr181-firewall | Chains, rules, levels, policies |
| `Device.NAT` | tr181-nat | NAT settings, PortMapping rules |
| `Device.WiFi` | tr181-wifi | Radios, SSIDs, AccessPoints, stations |
| `Device.Bridging` | tr181-bridging | Bridges, ports, VLANs |
| `Device.IP` | tr181-netmodel | IP interfaces, IPv4/IPv6 addresses |
| `Device.Ethernet` | tr181-netmodel | Ethernet interfaces and links |
| `Device.DHCPv4` | tr181-dhcp | DHCP server pools and clients |
| `Device.Routing` | tr181-routing | Routing tables and forwarding entries |
| `Device.QoS` | tr181-qos | QoS classification, queues, shapers |

### Reference Sources

Before generating a script, gather domain knowledge:

1. **Broadband Forum TR-181 spec**: https://device-data-model.broadband-forum.org/
2. **prpl Foundation plugins**: `https://gitlab.com/prpl-foundation/components/core/plugins/tr181-{name}`
3. **prplOS docs**: `https://prpl-foundation.gitlab.io/prplos/feeds/feed-prpl/{Object}..html`
4. **BBF data model XML**: https://github.com/BroadbandForum/device-data-model

Search these sources to understand the object hierarchy, key attributes, and relationships before writing the script.

## Workflow

### 1. Identify the Target Object

When the user asks to visualize a TR-181 object:

```bash
# Check what data exists in the dump file
grep -c "Device\.{Object}\." DM.txt

# See the object structure
grep "Device\.{Object}\." DM.txt | head -40
```

### 2. Research the Object Model

Search for background knowledge about the target object:
- Object hierarchy (parent/child relationships)
- Key attributes to display (Name, Alias, Enable, Status, etc.)
- Relationships to other objects (references, LowerLayers, etc.)
- Any enum or coded values that need human-readable mapping

### 3. Generate the Python Script

Create a script named `dm_visualizers/show_{object}.py` following these patterns:

#### File Structure (mandatory)

```python
#!/usr/bin/env python3
"""
Parse DM.txt and display TR-181 Device.{Object} as a text-based diagram.

Usage: python3 dm_visualizers/show_{object}.py [DM.txt]

References:
  - Broadband Forum TR-181 Device:2 Data Model
  - prpl Foundation tr181-{plugin} plugin
    https://gitlab.com/prpl-foundation/components/core/plugins/tr181-{plugin}
"""

import re
import shutil
import sys


def get_term_width():
    """Return terminal width, defaulting to 80."""
    try:
        return shutil.get_terminal_size((80, 24)).columns
    except Exception:
        return 80


def parse_dm(filepath):
    """Parse DM.txt into a dict of {path: value}."""
    dm = {}
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            m = re.match(r'^(Device\..+?)=(.*)$', line)
            if m:
                key = m.group(1)
                val = m.group(2).strip('"')
                dm[key] = val
    return dm


def get_attr(dm, prefix, attr):
    """Get attribute, trying with/without double dot."""
    for key in [f"{prefix}.{attr}", f"{prefix}..{attr}"]:
        if key in dm:
            return dm[key]
    return None
```

#### Design Rules

- **Adaptive layout**: Use `get_term_width()` to switch between compact (< 90 cols) and wide (>= 90 cols) formats.
- **Box drawing**: Use Unicode box characters (`┌─┐│├┤└─┘╔═╗║╠╣╚═╝`) for diagrams.
- **Helper functions**: Use `hline(char, width, left, right)` and `boxline(text, width)` for width-adaptive borders.
- **Emoji indicators**: 🟢 enabled, 🔴 disabled, ✅ accept, ❌ reject, 🚫 drop.
- **Instance discovery**: Use regex on DM keys to find object instances (e.g. `Device\.X\.(\d+)\.Name`).
- **Sorting**: Sort instances by ID or Order attribute.
- **Summary table**: Always end with a summary table of all instances.

#### Compact Layout (< 90 columns)

```
┌──────────────────────────────────────────────────┐
│  🟢 Instance 1: Name (Alias)
│  Key: value  Key: value
├──────────────────────────────────────────────────┤
│  #1 child_alias  detail  detail
│  #2 child_alias  detail  detail
└──────────────────────────────────────────────────┘
```

#### Wide Layout (>= 90 columns)

```
┌────────────────────────────────────────────────────────────────────────┐
│  🟢 Instance 1: Name (Alias)
│  Key: value  Key: value
├────────────────────────────────────────────────────────────────────────┤
│  #    Alias        Col1     Col2     Col3     Col4
│  ──── ──────────── ──────── ──────── ──────── ────────
│  1    name         val      val      val      val
└────────────────────────────────────────────────────────────────────────┘
```

### 4. Test the Script

```bash
python3 dm_visualizers/show_{object}.py DM.txt
```

Verify output renders correctly at different widths:

```bash
COLUMNS=60 python3 dm_visualizers/show_{object}.py DM.txt | head -30
COLUMNS=120 python3 dm_visualizers/show_{object}.py DM.txt | head -30
```

### 5. Generate Documentation (required)

Always create an explanation document under `doc/` named `tr181-{object}.md`.
Use `doc/tr181-fw.md` as the layout template and extract the same kinds of concepts:

- References to prpl Foundation, BBF, and any relevant XML/README sources
- Overview and key top-level parameters
- Object hierarchy diagram (parent/child relationships)
- Key selection or resolution mechanism(s) (e.g., Level → Policy → Chain)
- Naming conventions and any commonly used patterns
- Rule/entry parameters and meaning
- How to read the script output (overview box, per-instance tables, summary table)

## Existing Scripts in This Repository

| Script | Object | Key Features |
|---|---|---|
| `dm_visualizers/show_logical_stack.py` | `Device.Logical` | Recursive LowerLayers tree walk, WAN/LAN role detection |
| `dm_visualizers/show_firewall_rules.py` | `Device.Firewall` | Chain/Rule tables, Level→Policy→Chain resolution |

Study these scripts before generating a new one to maintain consistency.

## Conventions

- Only lines matching `Device.*=...` are parsed; object headers are ignored.
- Object paths may have trailing dots; normalize with `rstrip('.')`.
- Try both `obj.attr` and `obj..attr` lookups (some dumps use double dots).
- `LowerLayers` and similar references are comma-separated; trim whitespace and trailing dots.
- Display names prefer `Name`, fall back to `Alias`.
- Default input file is `DM.txt` in the current directory.
- Script takes an optional positional argument for the dump file path.

## Safety

- Scripts are read-only — they never modify the dump file.
- No external dependencies beyond Python 3 standard library.
- Always confirm with the user before committing generated scripts.
