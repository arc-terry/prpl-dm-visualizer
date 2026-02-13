#!/usr/bin/env python3
"""
Parse DM.txt and list the hierarchical relationship (top to bottom)
of each Device.Logical.Interface following BBF TR-181 InterfaceStack model.

Usage: python3 dm_visualizers/show_logical_stack.py [DM.txt]
"""

import re
import sys
from collections import defaultdict

from utils import get_attr as get_obj_attr, parse_dm, warn_narrow_width


def resolve_name(dm, obj_path):
    """Resolve a display-friendly name for an interface object."""
    obj = obj_path.rstrip('.')
    name = get_obj_attr(dm, obj, 'Name')
    alias = get_obj_attr(dm, obj, 'Alias')
    if name and name.strip():
        return name
    if alias and alias.strip():
        return alias
    return ''


def get_lower_layers(dm, obj_path):
    """Get LowerLayers references for an object, returned as a list."""
    val = get_obj_attr(dm, obj_path, 'LowerLayers')
    if not val:
        return []
    # Split comma-separated references
    refs = [r.strip().rstrip('.') for r in val.split(',') if r.strip()]
    return refs


def walk_stack(dm, obj_path, depth=0):
    """Recursively walk the interface stack from top to bottom."""
    obj = obj_path.rstrip('.')
    name = resolve_name(dm, obj)
    status = get_obj_attr(dm, obj, 'Status') or ''
    enable = get_obj_attr(dm, obj, 'Enable')

    # Build display label
    short = obj.replace('Device.', '')
    label = short
    if name:
        label += f'  ({name})'
    if status:
        label += f'  [{status}]'

    # Print with indentation
    indent = '    ' * depth
    connector = '└── ' if depth > 0 else ''
    print(f'{indent}{connector}{label}')

    # Get lower layers
    lowers = get_lower_layers(dm, obj)
    for lower in lowers:
        walk_stack(dm, lower, depth + 1)


def main():
    filepath = sys.argv[1] if len(sys.argv) > 1 else 'DM.txt'
    warn_narrow_width()

    print(f'Parsing: {filepath}')
    print()
    dm = parse_dm(filepath)

    # Find all Logical Interfaces
    logical_re = re.compile(r'^Device\.Logical\.Interface\.(\d+)\.Name$')
    logical_ids = []
    for key in dm:
        m = logical_re.match(key)
        if m:
            logical_ids.append(int(m.group(1)))
    logical_ids.sort()

    interfaces = []
    for lid in logical_ids:
        obj = f'Device.Logical.Interface.{lid}'
        wan_status = get_obj_attr(dm, obj, 'X_PRPLWARE-COM_WAN.Status') or ''
        lan_status = get_obj_attr(dm, obj, 'X_PRPLWARE-COM_LAN.Status') or ''
        role = 'WAN' if wan_status == 'Enabled' else 'LAN' if lan_status == 'Enabled' else '?'
        name = resolve_name(dm, obj)
        label = f'  Logical.Interface.{lid} "{name}"  (Role: {role})'
        interfaces.append({
            'id': lid,
            'obj': obj,
            'role': role,
            'label': label,
        })

    box_inner_width = 78
    if interfaces:
        box_inner_width = max(box_inner_width, max(len(entry['label']) for entry in interfaces))
    box_width = box_inner_width + 2

    header = (f'{"#":<4} {"Alias":<16} {"Role":<6} {"Status":<8} '
              f'{"IP Interface":<22} {"Eth Link":<22} {"Bottom Layer"}')
    summary_rows = []
    for entry in interfaces:
        lid = entry['id']
        obj = entry['obj']
        alias = get_obj_attr(dm, obj, 'Alias') or ''
        status = get_obj_attr(dm, obj, 'Status') or ''
        role = entry['role']

        # Walk to find IP and Ethernet layers
        ip_iface = ''
        eth_link = ''
        bottom = ''

        lowers = get_lower_layers(dm, obj)
        if lowers:
            ip_iface = lowers[0].replace('Device.', '')
            ip_lowers = get_lower_layers(dm, lowers[0])
            if ip_lowers:
                eth_link = ip_lowers[0].replace('Device.', '')
                eth_lowers = get_lower_layers(dm, ip_lowers[0])
                if eth_lowers:
                    bottom_obj = eth_lowers[0]
                    bottom_name = resolve_name(dm, bottom_obj)
                    bottom = bottom_obj.replace('Device.', '')
                    if bottom_name:
                        bottom += f' ({bottom_name})'

        summary_rows.append(
            f'{lid:<4} {alias:<16} {role:<6} {status:<8} '
            f'{ip_iface:<22} {eth_link:<22} {bottom}'
        )

    table_width = len(header)
    if summary_rows:
        table_width = max(table_width, max(len(row) for row in summary_rows))
    table_width = max(table_width, box_width)

    total = get_obj_attr(dm, 'Device.Logical', 'InterfaceNumberOfEntries')
    print(f'Device.Logical.InterfaceNumberOfEntries = {total}')
    print('=' * box_width)

    for entry in interfaces:
        lid = entry['id']
        obj = entry['obj']
        role = entry['role']
        label = entry['label']

        print()
        print(f'╔{"═" * box_inner_width}╗')
        print(f'║{label}{" " * (box_inner_width - len(label))}║')
        print(f'╚{"═" * box_inner_width}╝')
        print()
        walk_stack(dm, obj)
        print()

    # Summary table
    print()
    print('=' * table_width)
    print(header.ljust(table_width))
    print('-' * table_width)

    for row in summary_rows:
        print(row.ljust(table_width))

    print()


if __name__ == '__main__':
    main()
