#!/usr/bin/env python3
"""
Parse DM.txt and display TR-181 Device.WiFi radios, SSIDs, and access points
as a text-based visualized diagram.

Usage: python3 dm_visualizers/show_wifi.py [DM.txt]

References:
  - Broadband Forum TR-181 Device:2 Data Model (Device.WiFi)
  - prpl Foundation tr181-wifi plugin
    https://gitlab.com/prpl-foundation/components/core/plugins/tr181-wifi
"""

import os
import re
import signal
import sys

from utils import (
    box_width,
    boxline,
    display_width,
    fit_display,
    get_attr,
    hline,
    pad_display,
    parse_dm,
    warn_narrow_width,
)


WIDE_THRESHOLD = 90

if hasattr(signal, 'SIGPIPE'):
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)


def nonempty(value, fallback='-'):
    """Return a display-safe value for empty strings."""
    if value is None:
        return fallback
    value = str(value).strip()
    return value if value else fallback


def normalize_ref(value):
    """Normalize a TR-181 object reference."""
    if not value:
        return ''
    return value.strip().strip('"').rstrip('.')


def resolve_name(dm, prefix):
    """Resolve a display-friendly object name."""
    name = get_attr(dm, prefix, 'Name')
    alias = get_attr(dm, prefix, 'Alias')
    if name and name.strip():
        return name
    if alias and alias.strip():
        return alias
    return prefix.split('.')[-1]


def discover_radios(dm):
    """Discover WiFi radio instances."""
    radio_re = re.compile(r'^Device\.WiFi\.Radio\.(\d+)\.(Alias|Name)$')
    ids = set()
    for key in dm:
        match = radio_re.match(key)
        if match:
            ids.add(int(match.group(1)))

    radios = []
    for radio_id in sorted(ids):
        prefix = f'Device.WiFi.Radio.{radio_id}'
        radios.append({
            'id': radio_id,
            'prefix': prefix,
            'name': resolve_name(dm, prefix),
            'alias': nonempty(get_attr(dm, prefix, 'Alias')),
            'enable': get_attr(dm, prefix, 'Enable') or '0',
            'status': nonempty(get_attr(dm, prefix, 'Status')),
            'band': nonempty(get_attr(dm, prefix, 'OperatingFrequencyBand')),
            'standard': nonempty(get_attr(dm, prefix, 'OperatingStandards')),
            'channel': nonempty(get_attr(dm, prefix, 'Channel')),
            'auto_channel': get_attr(dm, prefix, 'AutoChannelEnable') or '0',
        })
    return radios


def discover_ssids(dm):
    """Discover WiFi SSID instances."""
    ssid_re = re.compile(r'^Device\.WiFi\.SSID\.(\d+)\.(Alias|Name|SSID)$')
    ids = set()
    for key in dm:
        match = ssid_re.match(key)
        if match:
            ids.add(int(match.group(1)))

    ssids = []
    for ssid_id in sorted(ids):
        prefix = f'Device.WiFi.SSID.{ssid_id}'
        ssids.append({
            'id': ssid_id,
            'prefix': prefix,
            'name': resolve_name(dm, prefix),
            'alias': nonempty(get_attr(dm, prefix, 'Alias')),
            'ssid': nonempty(get_attr(dm, prefix, 'SSID')),
            'bssid': nonempty(get_attr(dm, prefix, 'BSSID')),
            'enable': get_attr(dm, prefix, 'Enable') or '0',
            'status': nonempty(get_attr(dm, prefix, 'Status')),
            'lower_layers': normalize_ref(get_attr(dm, prefix, 'LowerLayers')),
        })
    return ssids


def discover_access_points(dm):
    """Discover WiFi access point instances."""
    ap_re = re.compile(r'^Device\.WiFi\.AccessPoint\.(\d+)\.(Alias|SSIDReference|RadioReference)$')
    ids = set()
    for key in dm:
        match = ap_re.match(key)
        if match:
            ids.add(int(match.group(1)))

    aps = []
    for ap_id in sorted(ids):
        prefix = f'Device.WiFi.AccessPoint.{ap_id}'
        aps.append({
            'id': ap_id,
            'prefix': prefix,
            'alias': nonempty(get_attr(dm, prefix, 'Alias')),
            'enable': get_attr(dm, prefix, 'Enable') or '0',
            'status': nonempty(get_attr(dm, prefix, 'Status')),
            'ssid_ref': normalize_ref(get_attr(dm, prefix, 'SSIDReference')),
            'radio_ref': normalize_ref(get_attr(dm, prefix, 'RadioReference')),
            'advertise': get_attr(dm, prefix, 'SSIDAdvertisementEnabled') or '0',
            'wmm': get_attr(dm, prefix, 'WMMEnable') or '0',
            'isolation': get_attr(dm, prefix, 'IsolationEnable') or '0',
        })
    return aps


def build_radio_ref_map(radios):
    """Build lookup keys for radio references."""
    ref_map = {}
    for radio in radios:
        prefix = radio['prefix']
        radio_id = str(radio['id'])
        keys = {
            prefix,
            f'Device.WiFi.Radio.{radio_id}',
            f'WiFi.Radio.{radio_id}',
        }
        alias = radio['alias']
        name = radio['name']
        if alias != '-':
            keys.add(f'WiFi.Radio.{alias}')
            keys.add(f'Device.WiFi.Radio.{alias}')
            keys.add(alias)
        if name not in ('-', alias):
            keys.add(f'WiFi.Radio.{name}')
            keys.add(f'Device.WiFi.Radio.{name}')
            keys.add(name)
        for key in keys:
            ref_map[normalize_ref(key)] = prefix
    return ref_map


def group_wifi(radios, ssids, aps):
    """Group SSIDs and APs by radio."""
    radio_map = {radio['prefix']: radio for radio in radios}
    radio_ref_map = build_radio_ref_map(radios)
    ssid_map = {ssid['prefix']: ssid for ssid in ssids}

    radio_groups = {radio['prefix']: {'ssids': [], 'aps': []} for radio in radios}
    unlinked_ssids = []
    unlinked_aps = []

    for ssid in ssids:
        radio_prefix = radio_ref_map.get(normalize_ref(ssid['lower_layers']))
        ssid['radio_prefix'] = radio_prefix or ''
        if radio_prefix and radio_prefix in radio_groups:
            radio_groups[radio_prefix]['ssids'].append(ssid)
        else:
            unlinked_ssids.append(ssid)

    for ap in aps:
        ssid_prefix = normalize_ref(ap['ssid_ref'])
        ssid = ssid_map.get(ssid_prefix)
        radio_prefix = ''
        if ssid and ssid.get('radio_prefix'):
            radio_prefix = ssid['radio_prefix']
        if not radio_prefix:
            radio_prefix = radio_ref_map.get(normalize_ref(ap['radio_ref']), '')
        ap['radio_prefix'] = radio_prefix
        if ssid:
            ap['ssid_prefix'] = ssid['prefix']
        else:
            ap['ssid_prefix'] = ''
        if radio_prefix and radio_prefix in radio_groups:
            radio_groups[radio_prefix]['aps'].append(ap)
        else:
            unlinked_aps.append(ap)

    for radio in radios:
        group = radio_groups[radio['prefix']]
        group['ssids'].sort(key=lambda entry: entry['id'])
        group['aps'].sort(key=lambda entry: entry['id'])
        group['ap_by_ssid'] = {}
        for ap in group['aps']:
            group['ap_by_ssid'].setdefault(ap.get('ssid_prefix') or '', []).append(ap)

    return radio_map, radio_groups, unlinked_ssids, unlinked_aps


def format_enable(value):
    """Format a binary enable field with an indicator."""
    return '🟢' if value == '1' else '🔴'


def format_bool(value):
    """Format a binary value as on/off."""
    return 'on' if value == '1' else 'off'


def print_wifi_overview(dm, radios, ssids, aps, width):
    """Print top-level Device.WiFi state."""
    lines = [
        f'Radios: {len(radios)} / {nonempty(get_attr(dm, "Device.WiFi", "RadioNumberOfEntries"))}',
        f'SSIDs: {len(ssids)} / {nonempty(get_attr(dm, "Device.WiFi", "SSIDNumberOfEntries"))}',
        f'Access Points: {len(aps)} / {nonempty(get_attr(dm, "Device.WiFi", "AccessPointNumberOfEntries"))}',
    ]
    box_w = box_width(width, lines, title='TR-181 WIFI OVERVIEW')
    print(hline('═', box_w, '╔', '╗'))
    print(f'║{"TR-181 WIFI OVERVIEW":^{box_w - 2}}║')
    print(hline('═', box_w, '╠', '╣'))
    for line in lines:
        print(boxline(line, box_w))
    print(hline('═', box_w, '╚', '╝'))
    print()


def compact_ssid_line(ssid):
    """Format one SSID line for compact layout."""
    return (
        f'  SSID #{ssid["id"]} {ssid["alias"]}  {format_enable(ssid["enable"])} '
        f'{ssid["status"]}  name={ssid["name"]}  ssid={ssid["ssid"]}'
    )


def compact_ap_line(ap):
    """Format one AP line for compact layout."""
    return (
        f'    AP #{ap["id"]} {ap["alias"]}  {format_enable(ap["enable"])} {ap["status"]}  '
        f'adv={format_bool(ap["advertise"])} wmm={format_bool(ap["wmm"])} '
        f'iso={format_bool(ap["isolation"])}'
    )


def print_radio_compact(radio, group, width):
    """Render one radio in compact layout."""
    lines = [
        f'{format_enable(radio["enable"])} Radio {radio["id"]}: {radio["name"]} ({radio["alias"]})',
        f'Status: {radio["status"]}  Band: {radio["band"]}  Std: {radio["standard"]}',
        f'Channel: {radio["channel"]}  AutoChannel: {format_bool(radio["auto_channel"])}',
    ]
    if group['ssids']:
        for ssid in group['ssids']:
            lines.append(compact_ssid_line(ssid))
            aps = group['ap_by_ssid'].get(ssid['prefix'], [])
            if aps:
                for ap in aps:
                    lines.append(compact_ap_line(ap))
            else:
                lines.append('    AP: (none)')
    else:
        lines.append('  SSID: (none)')

    box_w = box_width(width, lines)
    print(hline('─', box_w, '┌', '┐'))
    print(boxline(lines[0], box_w))
    print(boxline(lines[1], box_w))
    print(boxline(lines[2], box_w))
    print(hline('─', box_w, '├', '┤'))
    for line in lines[3:]:
        print(boxline(line, box_w))
    print(hline('─', box_w, '└', '┘'))
    print()


def render_table(columns, rows):
    """Build aligned text table rows."""
    widths = {}
    for key, label, min_width in columns:
        widths[key] = max(
            min_width,
            display_width(label),
            max((display_width(row.get(key, '')) for row in rows), default=0),
        )

    header = ' '.join(pad_display(label, widths[key]) for key, label, _ in columns)
    separator = ' '.join('─' * widths[key] for key, _, _ in columns)
    lines = [header, separator]
    for row in rows:
        lines.append(' '.join(pad_display(row.get(key, ''), widths[key]) for key, _, _ in columns))
    return lines


def print_subtable(title, columns, rows, width):
    """Print a titled subtable inside a box."""
    lines = [title]
    if rows:
        lines.extend(render_table(columns, rows))
    else:
        lines.append('(none)')
    box_w = box_width(width, lines)
    print(hline('─', box_w, '┌', '┐'))
    print(boxline(lines[0], box_w))
    print(hline('─', box_w, '├', '┤'))
    for idx, line in enumerate(lines[1:], start=1):
        if idx == 2 and len(lines) > 2:
            print(boxline(line, box_w, fill='─'))
        else:
            print(boxline(line, box_w))
    print(hline('─', box_w, '└', '┘'))


def print_radio_wide(radio, group, width):
    """Render one radio in wide layout."""
    header_lines = [
        f'{format_enable(radio["enable"])} Radio {radio["id"]}: {radio["name"]} ({radio["alias"]})',
        f'Status: {radio["status"]}  Band: {radio["band"]}  Standard: {radio["standard"]}',
        f'Channel: {radio["channel"]}  AutoChannel: {format_bool(radio["auto_channel"])}',
    ]
    box_w = box_width(width, header_lines)
    print(hline('─', box_w, '┌', '┐'))
    for line in header_lines:
        print(boxline(line, box_w))
    print(hline('─', box_w, '└', '┘'))

    ssid_rows = []
    for ssid in group['ssids']:
        ssid_rows.append({
            'id': str(ssid['id']),
            'alias': ssid['alias'],
            'name': ssid['name'],
            'ssid': ssid['ssid'],
            'en': format_enable(ssid['enable']),
            'status': ssid['status'],
            'bssid': ssid['bssid'],
        })
    print_subtable(
        'SSIDs',
        [
            ('id', '#', 2),
            ('alias', 'Alias', 10),
            ('name', 'Name', 10),
            ('ssid', 'SSID', 12),
            ('en', 'En', 2),
            ('status', 'Status', 8),
            ('bssid', 'BSSID', 17),
        ],
        ssid_rows,
        width,
    )
    print()

    ap_rows = []
    for ssid in group['ssids']:
        aps = group['ap_by_ssid'].get(ssid['prefix'], [])
        for ap in aps:
            ap_rows.append({
                'id': str(ap['id']),
                'alias': ap['alias'],
                'ssid': ssid['ssid'],
                'en': format_enable(ap['enable']),
                'status': ap['status'],
                'adv': format_bool(ap['advertise']),
                'wmm': format_bool(ap['wmm']),
                'iso': format_bool(ap['isolation']),
            })
    print_subtable(
        'Access Points',
        [
            ('id', '#', 2),
            ('alias', 'Alias', 10),
            ('ssid', 'SSID', 12),
            ('en', 'En', 2),
            ('status', 'Status', 8),
            ('adv', 'Advertise', 9),
            ('wmm', 'WMM', 3),
            ('iso', 'Isolation', 9),
        ],
        ap_rows,
        width,
    )
    print()


def print_radio(radio, group, width):
    """Render one radio block."""
    if width < WIDE_THRESHOLD:
        print_radio_compact(radio, group, width)
    else:
        print_radio_wide(radio, group, width)


def print_unlinked(title, rows, width):
    """Print unlinked SSID or AP rows."""
    box_w = box_width(width, [title] + rows)
    print(hline('─', box_w, '┌', '┐'))
    print(boxline(title, box_w))
    print(hline('─', box_w, '├', '┤'))
    if rows:
        for line in rows:
            print(boxline(line, box_w))
    else:
        print(boxline('(none)', box_w))
    print(hline('─', box_w, '└', '┘'))
    print()


def print_summary(radios, radio_groups, width):
    """Print radio summary table."""
    rows = []
    name_width = 14 if width < WIDE_THRESHOLD else 18
    band_width = 7 if width < WIDE_THRESHOLD else 8
    for radio in radios:
        group = radio_groups[radio['prefix']]
        rows.append({
            'id': str(radio['id']),
            'name': fit_display(radio['name'], name_width),
            'band': fit_display(radio['band'], band_width),
            'channel': radio['channel'],
            'status': radio['status'],
            'ssid': str(len(group['ssids'])),
            'ap': str(len(group['aps'])),
        })

    lines = ['  WIFI RADIO SUMMARY']
    lines.extend(render_table(
        [
            ('id', 'ID', 2),
            ('name', 'Radio', name_width),
            ('band', 'Band', band_width),
            ('channel', 'Ch', 2),
            ('status', 'Status', 8),
            ('ssid', 'SSIDs', 5),
            ('ap', 'APs', 3),
        ],
        rows,
    ))
    summary_width = max(width, max(display_width(line) for line in lines))
    print(hline('═', summary_width))
    print(lines[0])
    print(hline('═', summary_width))
    for line in lines[1:]:
        print(line)
    print()


def main():
    filepath = sys.argv[1] if len(sys.argv) > 1 else 'DM.txt'
    width = warn_narrow_width()

    print(f'Parsing: {filepath}')
    print()
    dm = parse_dm(filepath)

    radios = discover_radios(dm)
    ssids = discover_ssids(dm)
    aps = discover_access_points(dm)

    print_wifi_overview(dm, radios, ssids, aps, width)

    if not radios:
        print('No WiFi radios found.')
        return

    _, radio_groups, unlinked_ssids, unlinked_aps = group_wifi(radios, ssids, aps)

    for radio in radios:
        print_radio(radio, radio_groups[radio['prefix']], width)

    unlinked_ssid_lines = [
        f'SSID #{ssid["id"]} {ssid["alias"]}  name={ssid["name"]}  '
        f'ssid={ssid["ssid"]}  lower={ssid["lower_layers"]}'
        for ssid in unlinked_ssids
    ]
    print_unlinked('Unlinked SSIDs', unlinked_ssid_lines, width)

    unlinked_ap_lines = [
        f'AP #{ap["id"]} {ap["alias"]}  ssid-ref={nonempty(ap["ssid_ref"])}  '
        f'radio-ref={nonempty(ap["radio_ref"])}'
        for ap in unlinked_aps
    ]
    print_unlinked('Unlinked Access Points', unlinked_ap_lines, width)

    print_summary(radios, radio_groups, width)


if __name__ == '__main__':
    try:
        main()
    except BrokenPipeError:
        try:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
        finally:
            raise SystemExit(0)
