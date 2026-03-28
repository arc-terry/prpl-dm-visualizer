# TR-181 Device.Bridging — How It Works

## References

- [Broadband Forum TR-181 Data Model](https://device-data-model.broadband-forum.org/)
- [prpl Foundation tr181-bridging plugin (GitLab)](https://gitlab.com/prpl-foundation/components/core/plugins/tr181-bridging)
- [prplOS Bridging Documentation](https://prpl-foundation.gitlab.io/prplos/feeds/feed-prpl/Bridging..html)
- [BBF cwmp-data-models bridging XML](https://github.com/BroadbandForum/cwmp-data-models/blob/master/tr-181-2-18-1-bridging.xml)

## Overview

The TR-181 `Device.Bridging` object models bridge domains and their member ports. In this
repo's dumps, the most useful operational view is bridge-centric: one bridge object with
its nested `Port.{i}` entries and the `LowerLayers` references that bind ports to Ethernet
or WiFi objects.

## Object Hierarchy

```
Device.Bridging
└── Bridge.{i}
    ├── Port.{i}
    └── STP
```

## What The Visualizer Shows

The visualizer focuses on:

- bridge identity and state
- bridge STP state
- port membership and attachment

For each port it shows alias, name, enable state, status, type, management-port flag,
PVID, and `LowerLayers`.

It intentionally excludes port statistics and detailed VLAN tables in v1.

## Reading the Output

The script prints:

1. an overview box with total bridge count
2. one section per bridge
3. a per-bridge port list or table
4. a final bridge summary table

The layout adapts to terminal width:

- **≥ 90 columns**: table layout for ports
- **< 90 columns**: stacked port details in a compact card
