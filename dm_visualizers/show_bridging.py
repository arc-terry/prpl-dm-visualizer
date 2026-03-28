#!/usr/bin/env python3
"""
Parse DM.txt and display TR-181 Device.Bridging bridges and ports
as a text-based visualized diagram.

Usage: python3 dm_visualizers/show_bridging.py [DM.txt]

References:
  - Broadband Forum TR-181 Device:2 Data Model (Device.Bridging)
  - prpl Foundation tr181-bridging plugin
    https://gitlab.com/prpl-foundation/components/core/plugins/tr181-bridging
"""

import re
import signal
import sys

from utils import box_width, boxline, display_width, fit_display, get_attr, hline, pad_display, parse_dm, warn_narrow_width

WIDE_THRESHOLD = 90

if hasattr(signal, 'SIGPIPE'):
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)


def nonempty(value, fallback='-'):
    if value is None:
        return fallback
    value = str(value).strip()
    return value if value else fallback


def split_refs(value):
    if not value:
        return []
    return [part.strip().rstrip('.') for part in str(value).split(',') if part.strip()]


def format_enable(value):
    return '🟢' if value == '1' else '🔴'


def format_bool(value):
    return 'yes' if value == '1' else 'no'


def discover_ports(dm, bridge_id):
    port_re = re.compile(rf'^Device\.Bridging\.Bridge\.{bridge_id}\.Port\.(\d+)\.(Alias|Status)$')
    ids = set()
    for key in dm:
        match = port_re.match(key)
        if match:
            ids.add(int(match.group(1)))

    ports = []
    for port_id in sorted(ids):
        prefix = f'Device.Bridging.Bridge.{bridge_id}.Port.{port_id}'
        ports.append({
            'id': port_id,
            'alias': nonempty(get_attr(dm, prefix, 'Alias')),
            'name': nonempty(get_attr(dm, prefix, 'Name')),
            'enable': get_attr(dm, prefix, 'Enable') or '0',
            'status': nonempty(get_attr(dm, prefix, 'Status')),
            'type': nonempty(get_attr(dm, prefix, 'Type')),
            'mgmt': get_attr(dm, prefix, 'ManagementPort') or '0',
            'pvid': nonempty(get_attr(dm, prefix, 'PVID')),
            'lower': ', '.join(split_refs(get_attr(dm, prefix, 'LowerLayers'))) or '-',
        })
    return ports


def discover_bridges(dm):
    bridge_re = re.compile(r'^Device\.Bridging\.Bridge\.(\d+)\.(Alias|Status)$')
    ids = set()
    for key in dm:
        match = bridge_re.match(key)
        if match:
            ids.add(int(match.group(1)))

    bridges = []
    for bridge_id in sorted(ids):
        prefix = f'Device.Bridging.Bridge.{bridge_id}'
        bridges.append({
            'id': bridge_id,
            'alias': nonempty(get_attr(dm, prefix, 'Alias')),
            'enable': get_attr(dm, prefix, 'Enable') or '0',
            'status': nonempty(get_attr(dm, prefix, 'Status')),
            'ports': nonempty(get_attr(dm, prefix, 'PortNumberOfEntries')),
            'vlans': nonempty(get_attr(dm, prefix, 'VLANNumberOfEntries')),
            'vlan_ports': nonempty(get_attr(dm, prefix, 'VLANPortNumberOfEntries')),
            'stp_enable': get_attr(dm, f'{prefix}.STP', 'Enable') or '0',
            'stp_status': nonempty(get_attr(dm, f'{prefix}.STP', 'Status')),
            'port_rows': discover_ports(dm, bridge_id),
        })
    return bridges


def render_table(columns, rows):
    widths = {}
    for key, label, minimum in columns:
        widths[key] = max(minimum, display_width(label), max((display_width(row.get(key, '')) for row in rows), default=0))
    header = ' '.join(pad_display(label, widths[key]) for key, label, _ in columns)
    separator = ' '.join('─' * widths[key] for key, _, _ in columns)
    lines = [header, separator]
    for row in rows:
        lines.append(' '.join(pad_display(row.get(key, ''), widths[key]) for key, _, _ in columns))
    return lines


def print_overview(dm, bridges, width):
    lines = [f'Bridges: {len(bridges)} / {nonempty(get_attr(dm, "Device.Bridging", "BridgeNumberOfEntries"))}']
    box_w = box_width(width, lines, title='TR-181 BRIDGING OVERVIEW')
    print(hline('═', box_w, '╔', '╗'))
    print(f'║{"TR-181 BRIDGING OVERVIEW":^{box_w - 2}}║')
    print(hline('═', box_w, '╠', '╣'))
    for line in lines:
        print(boxline(line, box_w))
    print(hline('═', box_w, '╚', '╝'))
    print()


def print_bridge_compact(bridge, width):
    lower_w = max(width - 12, 24)
    lines = [
        f'{format_enable(bridge["enable"])} Bridge {bridge["id"]}: {bridge["alias"]}',
        f'Status: {bridge["status"]}  Ports: {bridge["ports"]}  VLANs: {bridge["vlans"]}',
        f'STP: {format_bool(bridge["stp_enable"])} ({bridge["stp_status"]})',
    ]
    if bridge['port_rows']:
        for port in bridge['port_rows']:
            lines.append(
                f'  Port #{port["id"]} {port["alias"]}  {format_enable(port["enable"])} {port["status"]}  '
                f'type={port["type"]} mgmt={format_bool(port["mgmt"])} pvid={port["pvid"]}'
            )
            lines.append(f'    name={port["name"]}  lower={fit_display(port["lower"], lower_w).rstrip()}')
    else:
        lines.append('  Port: (none)')

    box_w = box_width(width, lines)
    print(hline('─', box_w, '┌', '┐'))
    for line in lines[:3]:
        print(boxline(line, box_w))
    print(hline('─', box_w, '├', '┤'))
    for line in lines[3:]:
        print(boxline(line, box_w))
    print(hline('─', box_w, '└', '┘'))
    print()


def print_subtable(title, columns, rows, width):
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


def print_bridge_wide(bridge, width):
    header_lines = [
        f'{format_enable(bridge["enable"])} Bridge {bridge["id"]}: {bridge["alias"]}',
        f'Status: {bridge["status"]}  Ports: {bridge["ports"]}  VLANs: {bridge["vlans"]}  VLAN Ports: {bridge["vlan_ports"]}',
        f'STP: {format_bool(bridge["stp_enable"])} ({bridge["stp_status"]})',
    ]
    box_w = box_width(width, header_lines)
    print(hline('─', box_w, '┌', '┐'))
    for line in header_lines:
        print(boxline(line, box_w))
    print(hline('─', box_w, '└', '┘'))
    rows = []
    lower_w = max(18, width - 70)
    for port in bridge['port_rows']:
        rows.append({
            'id': str(port['id']),
            'alias': port['alias'],
            'name': port['name'],
            'en': format_enable(port['enable']),
            'status': port['status'],
            'type': port['type'],
            'mgmt': format_bool(port['mgmt']),
            'pvid': port['pvid'],
            'lower': fit_display(port['lower'], lower_w).rstrip(),
        })
    print_subtable(
        'Ports',
        [
            ('id', '#', 2),
            ('alias', 'Alias', 10),
            ('name', 'Name', 10),
            ('en', 'En', 2),
            ('status', 'Status', 8),
            ('type', 'Type', 14),
            ('mgmt', 'Mgmt', 4),
            ('pvid', 'PVID', 4),
            ('lower', 'LowerLayers', 18),
        ],
        rows,
        width,
    )
    print()


def print_bridge(bridge, width):
    if width < WIDE_THRESHOLD:
        print_bridge_compact(bridge, width)
    else:
        print_bridge_wide(bridge, width)


def print_summary(bridges, width):
    rows = []
    alias_w = 12 if width < WIDE_THRESHOLD else 14
    for bridge in bridges:
        rows.append({
            'id': str(bridge['id']),
            'alias': fit_display(bridge['alias'], alias_w),
            'status': bridge['status'],
            'ports': bridge['ports'],
            'stp': bridge['stp_status'],
        })
    lines = ['  BRIDGE SUMMARY']
    lines.extend(render_table(
        [
            ('id', 'ID', 2),
            ('alias', 'Alias', alias_w),
            ('status', 'Status', 8),
            ('ports', 'Ports', 5),
            ('stp', 'STP', 8),
        ],
        rows,
    ))
    total_w = max(width, max(display_width(line) for line in lines))
    print(hline('═', total_w))
    print(lines[0])
    print(hline('═', total_w))
    for line in lines[1:]:
        print(line)
    print()


def main():
    filepath = sys.argv[1] if len(sys.argv) > 1 else 'DM.txt'
    width = warn_narrow_width()
    print(f'Parsing: {filepath}')
    print()
    dm = parse_dm(filepath)
    bridges = discover_bridges(dm)
    print_overview(dm, bridges, width)
    if not bridges:
        print('No bridges found.')
        return
    for bridge in bridges:
        print_bridge(bridge, width)
    print_summary(bridges, width)


if __name__ == '__main__':
    main()
