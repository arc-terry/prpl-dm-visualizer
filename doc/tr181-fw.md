# TR-181 Device.Firewall — How It Works

## References

- [Broadband Forum TR-181 Data Model](https://device-data-model.broadband-forum.org/)
- [prpl Foundation tr181-firewall plugin (GitLab)](https://gitlab.com/prpl-foundation/components/core/plugins/tr181-firewall)
- [prplOS Firewall Documentation](https://prpl-foundation.gitlab.io/prplos/feeds/feed-prpl/Firewall..html)
- [BBF cwmp-data-models firewall XML](https://github.com/BroadbandForum/cwmp-data-models/blob/master/tr-181-2-18-1-firewall.xml)

## Overview

The TR-181 `Device.Firewall` object models firewall functionality for CPE devices managed via TR-069 or USP. It is structured as a hierarchy of **Levels**, **Policies**, **Chains**, and **Rules**, mapping to backend engines like Netfilter/iptables on Linux.

Key top-level parameters:

| Parameter | Description |
|---|---|
| `Enable` | Whether the firewall is active (1=on) |
| `Type` | `Stateful` (tracks connection state) or `Stateless` |
| `Config` | `Policy` (rule sets selected by level) or `Advanced` |
| `PolicyLevel` | Points to the active `Firewall.Level` instance |
| `DefaultPolicy` | Default action when no rule matches (typically `Drop`) |

## Object Hierarchy

```
Device.Firewall
├── Level.{i}            ← Security levels (Low, Medium, High, Custom)
│   └── Policies         ← References to Policy instances for this level
├── Policy.{i}           ← Binds a traffic direction to a Chain
│   └── Chain            ← Reference to a Chain by alias
├── Chain.{i}            ← Ordered collection of rules (maps to iptables chain)
│   └── Rule.{i}         ← Individual firewall rule
├── InterfaceSetting.{i} ← Per-interface firewall settings
└── Service.{i}          ← Predefined service definitions
```

## Level → Policy → Chain Selection

When `PolicyLevel` is set, the firewall activates through a three-step indirection:

1. **Level**: `Device.Firewall.PolicyLevel` selects a `Level.{i}` (e.g. `Alias=='Medium'`)
2. **Policies**: The Level's `Policies` parameter lists `Policy.{i}` references for each traffic direction
3. **Chain**: Each Policy's `Chain` parameter points to a specific `Chain.{i}` by alias

### Example: Medium Policy

```
PolicyLevel = Firewall.Level.[Alias=='Medium']
    → Level.2.Policies = WAN2LAN_medium, IPV6_WAN2LAN_medium, ...
        → Policy "WAN2LAN_medium"     → Chain.[Alias=='Medium']     → Chain 3 (FORWARD_L_Medium)
        → Policy "IPV6_WAN2LAN_medium" → Chain.[Alias=='IPV6_Medium'] → Chain 6 (FORWARD6_L_Medium)
```

### Active inbound chains per level

| Level | IPv4 Chain | IPv6 Chain |
|---|---|---|
| Low | `FORWARD_L_Low` (accept all) | `FORWARD6_L_Low` (accept all) |
| Medium | `FORWARD_L_Medium` (accept RELATED,ESTABLISHED only) | `FORWARD6_L_Medium` (same) |
| High | `FORWARD_L_High` (accept RELATED,ESTABLISHED only) | `FORWARD6_L_High` (same) |
| Custom | `FORWARD_L_Custom_In` (user-defined) | `FORWARD_L_Custom_In` (same) |

The `DefaultPolicy` for all levels is `Drop`, so any traffic not matching a rule is dropped.

## Chain Naming Convention

| Chain Name Pattern | Purpose |
|---|---|
| `FORWARD_Sentinel` | Sentinel/catch-all chain on the FORWARD path |
| `FORWARD_L_Low/Medium/High` | IPv4 inbound filtering at each security level |
| `FORWARD6_L_Low/Medium/High` | IPv6 inbound filtering at each security level |
| `FORWARD_L_High_Out` | IPv4 outbound port-based allowlist (High level) |
| `FORWARD6_L_High_Out` | IPv6 outbound port-based allowlist (High level) |
| `FORWARD_L_Custom_In` | User-defined custom inbound rules |
| `FORWARD_L_Custom_Out` | User-defined custom outbound rules |
| `LCM` | Lifecycle management chain |

## Rule Parameters

Each `Chain.{i}.Rule.{i}` contains:

| Parameter | Description | Example |
|---|---|---|
| `Order` | Evaluation order (first match wins) | `1` |
| `Alias` | Human-readable name | `ssh`, `http`, `cstate` |
| `Enable` | Whether the rule is active | `1` |
| `Target` | Action on match: `Accept`, `Drop`, `Reject` | `Accept` |
| `Protocol` | IP protocol number (`6`=TCP, `17`=UDP, `-1`=any) | `6` |
| `DestPort` | Destination port (`-1`=any) | `22` |
| `DestPortRangeMax` | End of port range (`-1`=single port) | `-1` |
| `SourcePort` | Source port (`-1`=any) | `-1` |
| `SourceIP` / `DestIP` | IP address filter (empty=any) | `""` |
| `ConnectionState` | Conntrack match | `RELATED,ESTABLISHED` |
| `IPVersion` | IP version filter (`-1`=both) | `-1` |
| `Log` | Whether to log matching packets | `1` |

## InterfaceSetting

`Device.Firewall.InterfaceSetting.{i}` binds firewall behavior to specific logical interfaces:

| Setting | WAN | WAN-Cellular | LAN | Guest |
|---|---|---|---|---|
| Interface | `Logical.Interface.1` | `Logical.Interface.8` | `IP.Interface.3` | `IP.Interface.4` |
| ICMP Echo (v4) | blocked | blocked | allowed | allowed |
| Spoofing Protection (v4) | off | off | on | on |
| Stealth Mode | on | on | off | off |

## Outbound Chains

The `_Out` chains (`High_Out`, `IPV6_High_Out`, `Custom_Out`) are not selected via the Level/Policy mechanism. They control outbound FORWARD traffic and are typically always active or wired separately by the tr181-firewall plugin. These implement a whitelist of allowed outbound services (FTP, SSH, DNS, HTTP, HTTPS, etc.), with catch-all reject rules at the end.

## Reading show_firewall_rules.py Output

The script parses `DM.txt` and displays:

1. **Overview box**: Global firewall settings (enable, type, config, policy, chain count)
2. **Per-chain diagram**: Each chain with its rules in a table showing order, alias, target (✅/❌/🚫), protocol, ports, IPs, and connection state
3. **Summary table**: All chains at a glance with enable status and rule count

The layout adapts automatically to terminal width:
- **≥ 90 columns**: Full table with separate columns for each field
- **< 90 columns**: Compact card format with key fields on a single line
