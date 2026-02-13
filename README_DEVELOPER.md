# Developer Guide: Creating a New Visualizer with Copilot CLI

This guide shows a simple, step-by-step Copilot CLI flow for adding a new visualizer for a prpl-based TR-181 data model object.

## Prerequisites

- Python 3 installed
- Run commands from the repo root

## Step-by-step (Copilot CLI)

1) List available skills to confirm the visualizer helper exists:
```
/skills list
```

2) Inspect the visualizer skill so Copilot follows the repo’s conventions:
```
/skills info tr181-dm-visualizer
```

3) Ask Copilot to generate a new visualizer and documentation.
   Ensure the script name starts with `show_` (so `visualize.py` discovers it) and
   reuse helpers from `dm_visualizers/utils.py`.
   Example (simple object: `Device.IP`):
```
Please use the tr181-dm-visualizer skill to add a new visualizer for Device.IP.
Create dm_visualizers/show_ip.py with a Usage line in the module docstring.
Use helpers from dm_visualizers/utils.py (parse_dm, get_attr, boxline, box_width, warn_narrow_width).
Parse Device.*=value lines only, normalize trailing dots, and include a summary table.
Also add doc/tr181-ip.md using doc/tr181-fw.md as the layout template.
```

4) Review the proposed changes:
```
git --no-pager diff
```

5) Run the new script on demo data (or your own DM.txt):
```
python3 dm_visualizers/show_ip.py demo_dm_data/pon-wan-DM.txt
```

6) Optionally run via the controller (auto-detects new scripts):
```
python3 visualize.py show_ip demo_dm_data/pon-wan-DM.txt
```

7) Quick layout check (compact vs. wide):
```
COLUMNS=60 python3 dm_visualizers/show_ip.py demo_dm_data/pon-wan-DM.txt | head -30
COLUMNS=120 python3 dm_visualizers/show_ip.py demo_dm_data/pon-wan-DM.txt | head -30
```

## Minimal example prompt

If you want the shortest possible instruction, use this single prompt:
```
Use the tr181-dm-visualizer skill to add dm_visualizers/show_ip.py and doc/tr181-ip.md for Device.IP, following existing conventions and shared utils.
```
