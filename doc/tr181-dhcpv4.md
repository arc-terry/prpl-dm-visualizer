# TR-181 Device.DHCPv4 — How It Works

## References

- [Broadband Forum TR-181 Data Model](https://device-data-model.broadband-forum.org/)
- [prpl Foundation tr181-dhcp plugin (GitLab)](https://gitlab.com/prpl-foundation/components/core/plugins/tr181-dhcp)
- [prplOS DHCP Documentation](https://prpl-foundation.gitlab.io/prplos/feeds/feed-prpl/DHCPv4..html)
- [BBF cwmp-data-models DHCPv4 XML](https://github.com/BroadbandForum/cwmp-data-models/blob/master/tr-181-2-18-1-dhcpv4.xml)

## Overview

The TR-181 `Device.DHCPv4` object covers both DHCP client and server behavior.
In these dumps, the most useful operational view is:

- `Client.{i}` for WAN- or service-facing DHCP clients
- `Server.Pool.{i}` for LAN-side lease pools

## Object Hierarchy

```
Device.DHCPv4
├── Client.{i}
└── Server
    └── Pool.{i}
```

## What The Visualizer Shows

For clients it shows:

- alias and interface
- administrative and operational state
- DHCP state
- leased IP, mask, server, routers, DNS, and lease time remaining

For server pools it shows:

- alias and interface
- pool order and status
- address range and subnet mask
- routers, DNS servers, domain name, and lease time

It intentionally excludes request/sent option tables and deeper option detail in v1.

## Reading the Output

The script prints:

1. an overview box with client and pool counts
2. a DHCP client section
3. a server pool section
4. separate summary tables for clients and pools

The layout adapts to terminal width:

- **≥ 90 columns**: aligned client and pool tables
- **< 90 columns**: compact stacked summaries
