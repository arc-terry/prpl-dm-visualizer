# TR-181 Device.WiFi — How It Works

## References

- [Broadband Forum TR-181 Data Model](https://device-data-model.broadband-forum.org/)
- [prpl Foundation tr181-wifi plugin (GitLab)](https://gitlab.com/prpl-foundation/components/core/plugins/tr181-wifi)
- [prplOS WiFi Documentation](https://prpl-foundation.gitlab.io/prplos/feeds/feed-prpl/WiFi..html)
- [BBF cwmp-data-models WiFi XML](https://github.com/BroadbandForum/cwmp-data-models/blob/master/tr-181-2-18-1-wifi.xml)

## Overview

The TR-181 `Device.WiFi` object models the wireless subsystem. For visualizing the
operational topology, the most useful runtime structure is:

- `Radio.{i}` for physical radios
- `SSID.{i}` for broadcast network instances
- `AccessPoint.{i}` for AP-facing service state bound to those SSIDs

This visualizer focuses on those three layers and their relationships.

Key top-level parameters:

| Parameter | Description |
|---|---|
| `RadioNumberOfEntries` | Number of WiFi radio instances |
| `SSIDNumberOfEntries` | Number of SSID instances |
| `AccessPointNumberOfEntries` | Number of access point instances |

## Object Hierarchy

```
Device.WiFi
├── Radio.{i}         ← Physical radio and channel state
├── SSID.{i}          ← Logical wireless network bound to a radio
│   └── LowerLayers   ← Reference to Device.WiFi.Radio.{i}
└── AccessPoint.{i}   ← AP service state bound to an SSID
    ├── SSIDReference ← Reference to Device.WiFi.SSID.{i}
    └── RadioReference← Alias-style radio hint in some dumps
```

The visualizer intentionally excludes v1 details such as security objects, associated
devices, and the deeper `ChannelMgt` history tree.

## Radio → SSID → AccessPoint Linking

The script resolves the WiFi topology in two steps:

1. **SSID to Radio**: `Device.WiFi.SSID.{i}.LowerLayers` points to `Device.WiFi.Radio.{i}`
2. **AccessPoint to SSID**: `Device.WiFi.AccessPoint.{i}.SSIDReference` points to the SSID instance

`RadioReference` is used as a secondary hint because some dumps express it in alias-like
forms such as `WiFi.Radio.wl0` or `WiFi.Radio.radio0` instead of an instance path.

If a WiFi object cannot be linked cleanly, the visualizer keeps it visible in an
`unlinked` section rather than dropping it.

## Key Parameters

### Radio

| Parameter | Description | Example |
|---|---|---|
| `Alias` / `Name` | Display label for the radio | `wl0`, `radio0` |
| `Enable` | Administrative enable state | `1` |
| `Status` | Operational state | `Up`, `NotPresent` |
| `OperatingFrequencyBand` | Band used by the radio | `2.4GHz`, `5GHz`, `6GHz` |
| `OperatingStandards` | Active WiFi standard(s) | `ax`, `ax,be`, `bgn` |
| `Channel` | Current operating channel | `36` |
| `AutoChannelEnable` | Whether automatic channel selection is enabled | `0` |

### SSID

| Parameter | Description | Example |
|---|---|---|
| `Alias` / `Name` | Display label for the SSID object | `DEFAULT_RADIO0`, `wlan0p1.1` |
| `SSID` | Broadcast network name | `prplOS`, `PWHM_SSID2` |
| `BSSID` | MAC address used by the SSID | `08:00:27:62:80:90` |
| `Enable` | Administrative enable state | `1` |
| `Status` | Runtime status | `Down`, `Dormant` |
| `LowerLayers` | Reference to the bound radio | `Device.WiFi.Radio.1` |

### AccessPoint

| Parameter | Description | Example |
|---|---|---|
| `Alias` | Display label for the AP instance | `wl0`, `wlan0p1.1` |
| `Enable` | Administrative enable state | `1` |
| `Status` | Runtime status | `Enabled`, `Disabled` |
| `SSIDReference` | Bound SSID object | `Device.WiFi.SSID.4` |
| `RadioReference` | Secondary radio reference | `WiFi.Radio.wl0` |
| `SSIDAdvertisementEnabled` | Whether beacon advertisement is enabled | `1` |
| `WMMEnable` | Whether WMM is enabled | `1` |
| `IsolationEnable` | Whether client isolation is enabled | `0` |

## Reading `dm_visualizers/show_wifi.py` Output

The script parses `DM.txt` and displays:

1. **Overview box**: counts of radios, SSIDs, and access points
2. **Per-radio view**: one radio block with band, standard, channel, and auto-channel state
3. **Linked SSIDs and APs**: SSIDs grouped under the owning radio, with APs grouped under the SSID
4. **Unlinked sections**: WiFi objects that could not be resolved by reference
5. **Summary table**: all radios with band, channel, status, and counts of linked SSIDs/APs

The layout adapts automatically to terminal width:

- **≥ 90 columns**: separate SSID and AP tables inside each radio section
- **< 90 columns**: compact card layout with stacked SSID and AP lines

Display name resolution follows repo conventions:

- prefer `Name` when present
- fall back to `Alias`
- fall back to the instance id when both are blank
