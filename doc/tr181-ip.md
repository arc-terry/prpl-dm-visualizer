# TR-181 Device.IP — How It Works

## References

- [Broadband Forum TR-181 Data Model](https://device-data-model.broadband-forum.org/)
- [prpl Foundation tr181-netmodel plugin (GitLab)](https://gitlab.com/prpl-foundation/components/core/plugins/tr181-netmodel)
- [prplOS IP / netmodel Documentation](https://prpl-foundation.gitlab.io/prplos/feeds/feed-prpl/IP..html)
- [BBF cwmp-data-models IP XML](https://github.com/BroadbandForum/cwmp-data-models/blob/master/tr-181-2-18-1-ip.xml)

## Overview

The TR-181 `Device.IP` object models the device IP layer. In practice, the most useful
runtime state is under `Device.IP.Interface.{i}`, where each interface binds IP behavior
to a lower network object and exposes its configured IPv4 and IPv6 addresses.

Key top-level parameters:

| Parameter | Description |
|---|---|
| `IPv4Enable` / `IPv4Status` | Global IPv4 administrative and operational state |
| `IPv6Enable` / `IPv6Status` | Global IPv6 administrative and operational state |
| `InterfaceNumberOfEntries` | Number of `IP.Interface` instances |
| `ULAPrefix` | Base Unique Local Address prefix used for IPv6 ULA addressing |

## Object Hierarchy

```
Device.IP
├── Interface.{i}          ← Per-IP-layer interface
│   ├── IPv4Address.{i}    ← IPv4 addresses bound to the interface
│   ├── IPv6Address.{i}    ← IPv6 addresses bound to the interface
│   └── IPv6Prefix.{i}     ← Prefix objects referenced by IPv6Address entries
└── Diagnostics            ← Ping, throughput, and other IP diagnostics
```

The visualizer focuses on `Interface.{i}` and its nested address objects. `Diagnostics`
is intentionally omitted because it is large and not central to interface topology.

## How `IP.Interface` Maps the Stack

Each `Device.IP.Interface.{i}` represents an IP endpoint layered on top of another TR-181
network object. The `LowerLayers` parameter links it to the next lower object in the stack,
for example:

- `Device.Ethernet.Link.{i}`
- `Device.Ethernet.VLANTermination.{i}`
- another `Device.IP.Interface.{i}` in tunnel cases

Typical interface fields surfaced by the visualizer:

| Parameter | Description |
|---|---|
| `Alias` / `Name` | Human-friendly identifier; `Name` usually maps to the Linux interface name |
| `Enable` | Administrative enable state |
| `Status` | Operational status such as `Up`, `Down`, or `Unknown` |
| `Type` | Interface role such as `Normal`, `Loopback`, or `Tunnel` |
| `LowerLayers` | Reference to the underlying TR-181 object(s) |
| `IPv4Enable` / `IPv6Enable` | Whether the protocol family is enabled on this interface |
| `IPv4AddressNumberOfEntries` / `IPv6AddressNumberOfEntries` | Count of nested address objects |

## Address Objects

### IPv4Address

Each `Device.IP.Interface.{i}.IPv4Address.{i}` typically includes:

| Parameter | Description | Example |
|---|---|---|
| `Alias` | Address role/name | `primary`, `lan` |
| `Enable` | Administrative state | `1` |
| `Status` | Operational state | `Enabled`, `Disabled` |
| `AddressingType` | How the address is assigned | `Static`, `DHCP` |
| `IPAddress` | IPv4 address value | `192.168.1.1` |
| `SubnetMask` | IPv4 subnet mask | `255.255.255.0` |

### IPv6Address

Each `Device.IP.Interface.{i}.IPv6Address.{i}` typically includes:

| Parameter | Description | Example |
|---|---|---|
| `Alias` | Address role/name | `LLA`, `GUA`, `ULA` |
| `Enable` | Administrative state | `1` |
| `Status` | Object status | `Enabled`, `Disabled`, `Error` |
| `Origin` | Source of the address | `WellKnown`, `DHCPv6`, `AutoConfigured`, `Static` |
| `IPAddress` | IPv6 address value | `fe80::...` |
| `IPAddressStatus` | Address usability state | `Preferred`, `Invalid`, `Unknown` |
| `Prefix` | Reference to an `IPv6Prefix` object | `Device.IP.Interface.3.IPv6Prefix.2` |

Many dumps contain placeholder or empty IPv6 address values while the prefix reference and
status fields still explain what the stack is trying to configure. The visualizer preserves
those rows rather than filtering them out.

## Reading `dm_visualizers/show_ip.py` Output

The script parses `DM.txt` and displays:

1. **Overview box**: global `Device.IP` state for IPv4, IPv6, interface count, and ULA prefix
2. **Per-interface view**: one card per `IP.Interface` showing identity, state, `LowerLayers`, and protocol-family counts
3. **IPv4/IPv6 address tables**: nested address rows for each interface
4. **Summary table**: all interfaces at a glance with enable status, type, lower layer, and address counts

The layout adapts automatically to terminal width:

- **≥ 90 columns**: separate IPv4 and IPv6 tables with aligned columns
- **< 90 columns**: compact card layout with stacked address lines

Display name resolution follows repo conventions:

- prefer `Name` when present
- fall back to `Alias`
- fall back to the instance path if both are blank
