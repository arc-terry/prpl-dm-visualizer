#!/usr/bin/env python3
"""
Parse DM.txt and display TR-181 Device.IP interfaces and addresses
as a text-based visualized diagram.

Usage: python3 dm_visualizers/show_ip.py [DM.txt]

References:
  - Broadband Forum TR-181 Device:2 Data Model (Device.IP.Interface.{i})
  - prpl Foundation tr181-netmodel plugin
    https://gitlab.com/prpl-foundation/components/core/plugins/tr181-netmodel
"""

import re
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


def nonempty(value, fallback='-'):
    """Return a display-safe value for empty strings."""
    if value is None:
        return fallback
    value = str(value).strip()
    return value if value else fallback


def resolve_name(dm, prefix):
    """Resolve a display-friendly interface name."""
    name = get_attr(dm, prefix, 'Name')
    alias = get_attr(dm, prefix, 'Alias')
    if name and name.strip():
        return name
    if alias and alias.strip():
        return alias
    return prefix.replace('Device.IP.Interface.', 'if')


def split_refs(value):
    """Split a comma-separated list of object references."""
    if not value:
        return []
    return [part.strip().rstrip('.') for part in value.split(',') if part.strip()]


def discover_interfaces(dm):
    """Discover IP interface instances and their nested addresses."""
    iface_re = re.compile(r'^Device\.IP\.Interface\.(\d+)\.(Alias|Name)$')
    ids = set()
    for key in dm:
        match = iface_re.match(key)
        if match:
            ids.add(int(match.group(1)))

    interfaces = []
    for iface_id in sorted(ids):
        prefix = f'Device.IP.Interface.{iface_id}'
        interfaces.append({
            'id': iface_id,
            'prefix': prefix,
            'name': resolve_name(dm, prefix),
            'alias': nonempty(get_attr(dm, prefix, 'Alias')),
            'enable': get_attr(dm, prefix, 'Enable') or '0',
            'status': nonempty(get_attr(dm, prefix, 'Status')),
            'type': nonempty(get_attr(dm, prefix, 'Type')),
            'lower_layers': split_refs(get_attr(dm, prefix, 'LowerLayers')),
            'ipv4_enable': get_attr(dm, prefix, 'IPv4Enable') or '0',
            'ipv6_enable': get_attr(dm, prefix, 'IPv6Enable') or '0',
            'ipv4_count': int(get_attr(dm, prefix, 'IPv4AddressNumberOfEntries') or '0'),
            'ipv6_count': int(get_attr(dm, prefix, 'IPv6AddressNumberOfEntries') or '0'),
            'ipv4_addresses': discover_ipv4_addresses(dm, prefix),
            'ipv6_addresses': discover_ipv6_addresses(dm, prefix),
        })
    return interfaces


def discover_ipv4_addresses(dm, iface_prefix):
    """Find IPv4Address instances for an interface."""
    addr_re = re.compile(rf'^{re.escape(iface_prefix)}\.IPv4Address\.(\d+)\.(Alias|IPAddress)$')
    ids = set()
    for key in dm:
        match = addr_re.match(key)
        if match:
            ids.add(int(match.group(1)))

    addresses = []
    for addr_id in sorted(ids):
        prefix = f'{iface_prefix}.IPv4Address.{addr_id}'
        addresses.append({
            'id': addr_id,
            'alias': nonempty(get_attr(dm, prefix, 'Alias')),
            'enable': get_attr(dm, prefix, 'Enable') or '0',
            'status': nonempty(get_attr(dm, prefix, 'Status')),
            'addressing': nonempty(get_attr(dm, prefix, 'AddressingType')),
            'ip': nonempty(get_attr(dm, prefix, 'IPAddress')),
            'mask': nonempty(get_attr(dm, prefix, 'SubnetMask')),
        })
    return addresses


def discover_ipv6_addresses(dm, iface_prefix):
    """Find IPv6Address instances for an interface."""
    addr_re = re.compile(rf'^{re.escape(iface_prefix)}\.IPv6Address\.(\d+)\.(Alias|IPAddress|Prefix)$')
    ids = set()
    for key in dm:
        match = addr_re.match(key)
        if match:
            ids.add(int(match.group(1)))

    addresses = []
    for addr_id in sorted(ids):
        prefix = f'{iface_prefix}.IPv6Address.{addr_id}'
        addresses.append({
            'id': addr_id,
            'alias': nonempty(get_attr(dm, prefix, 'Alias')),
            'enable': get_attr(dm, prefix, 'Enable') or '0',
            'status': nonempty(get_attr(dm, prefix, 'Status')),
            'origin': nonempty(get_attr(dm, prefix, 'Origin')),
            'ip': nonempty(get_attr(dm, prefix, 'IPAddress')),
            'ip_status': nonempty(get_attr(dm, prefix, 'IPAddressStatus')),
            'prefix': nonempty(get_attr(dm, prefix, 'Prefix')),
        })
    return addresses


def print_ip_overview(dm, width):
    """Print top-level Device.IP state."""
    lines = [
        f'IPv4: enable={nonempty(get_attr(dm, "Device.IP", "IPv4Enable"))} '
        f'status={nonempty(get_attr(dm, "Device.IP", "IPv4Status"))}',
        f'IPv6: enable={nonempty(get_attr(dm, "Device.IP", "IPv6Enable"))} '
        f'status={nonempty(get_attr(dm, "Device.IP", "IPv6Status"))}',
        f'Interfaces: {nonempty(get_attr(dm, "Device.IP", "InterfaceNumberOfEntries"))}  '
        f'ULA Prefix: {nonempty(get_attr(dm, "Device.IP", "ULAPrefix"))}',
    ]
    box_w = box_width(width, lines, title='TR-181 IP OVERVIEW')
    print(hline('═', box_w, '╔', '╗'))
    print(f'║{"TR-181 IP OVERVIEW":^{box_w - 2}}║')
    print(hline('═', box_w, '╠', '╣'))
    for line in lines:
        print(boxline(line, box_w))
    print(hline('═', box_w, '╚', '╝'))
    print()


def format_enable(value):
    """Format a binary enable field with an indicator."""
    return '🟢' if value == '1' else '🔴'


def print_interface_compact(interface, width):
    """Render an interface in compact card layout."""
    lower_layers = ', '.join(interface['lower_layers']) if interface['lower_layers'] else '-'
    lines = [
        f'{format_enable(interface["enable"])} Interface {interface["id"]}: '
        f'{interface["name"]} ({interface["alias"]})',
        f'Status: {interface["status"]}  Type: {interface["type"]}',
        f'LowerLayers: {lower_layers}',
        f'IPv4: {format_enable(interface["ipv4_enable"])} count={interface["ipv4_count"]}    '
        f'IPv6: {format_enable(interface["ipv6_enable"])} count={interface["ipv6_count"]}',
    ]
    ipv4_lines = ['IPv4 Addresses']
    if interface['ipv4_addresses']:
        for addr in interface['ipv4_addresses']:
            ipv4_lines.append(
                f'#{addr["id"]} {addr["alias"]}  {format_enable(addr["enable"])} '
                f'{addr["status"]}  {addr["addressing"]}  {addr["ip"]}/{addr["mask"]}'
            )
    else:
        ipv4_lines.append('(none)')

    ipv6_lines = ['IPv6 Addresses']
    if interface['ipv6_addresses']:
        for addr in interface['ipv6_addresses']:
            ipv6_lines.append(
                f'#{addr["id"]} {addr["alias"]}  {format_enable(addr["enable"])} '
                f'{addr["status"]}  {addr["origin"]}  {addr["ip"]}  '
                f'ip-status={addr["ip_status"]}  prefix={addr["prefix"]}'
            )
    else:
        ipv6_lines.append('(none)')

    box_w = box_width(width, lines + ipv4_lines + ipv6_lines)
    print(hline('─', box_w, '┌', '┐'))
    for line in lines:
        print(boxline(line, box_w))
    print(hline('─', box_w, '├', '┤'))
    for line in ipv4_lines:
        print(boxline(line, box_w))
    print(hline('─', box_w, '├', '┤'))
    for line in ipv6_lines:
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


def print_address_table(title, columns, rows, width):
    """Print a titled address table inside a box."""
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


def print_interface_wide(interface, width):
    """Render an interface in wide layout with nested address tables."""
    lower_layers = ', '.join(interface['lower_layers']) if interface['lower_layers'] else '-'
    header_lines = [
        f'{format_enable(interface["enable"])} Interface {interface["id"]}: '
        f'{interface["name"]} ({interface["alias"]})',
        f'Status: {interface["status"]}  Type: {interface["type"]}',
        f'LowerLayers: {lower_layers}',
        f'IPv4: {format_enable(interface["ipv4_enable"])} count={interface["ipv4_count"]}    '
        f'IPv6: {format_enable(interface["ipv6_enable"])} count={interface["ipv6_count"]}',
    ]
    box_w = box_width(width, header_lines)
    print(hline('─', box_w, '┌', '┐'))
    for line in header_lines:
        print(boxline(line, box_w))
    print(hline('─', box_w, '└', '┘'))

    ipv4_rows = []
    for addr in interface['ipv4_addresses']:
        ipv4_rows.append({
            'id': str(addr['id']),
            'alias': addr['alias'],
            'en': format_enable(addr['enable']),
            'status': addr['status'],
            'mode': addr['addressing'],
            'ip': addr['ip'],
            'mask': addr['mask'],
        })
    print_address_table(
        'IPv4 Addresses',
        [
            ('id', '#', 2),
            ('alias', 'Alias', 10),
            ('en', 'En', 2),
            ('status', 'Status', 8),
            ('mode', 'Type', 8),
            ('ip', 'IP Address', 15),
            ('mask', 'SubnetMask', 15),
        ],
        ipv4_rows,
        width,
    )
    print()

    ipv6_rows = []
    for addr in interface['ipv6_addresses']:
        ipv6_rows.append({
            'id': str(addr['id']),
            'alias': addr['alias'],
            'en': format_enable(addr['enable']),
            'status': addr['status'],
            'origin': addr['origin'],
            'ip_status': addr['ip_status'],
            'ip': addr['ip'],
            'prefix': addr['prefix'],
        })
    print_address_table(
        'IPv6 Addresses',
        [
            ('id', '#', 2),
            ('alias', 'Alias', 10),
            ('en', 'En', 2),
            ('status', 'Status', 8),
            ('origin', 'Origin', 12),
            ('ip_status', 'IPStatus', 9),
            ('ip', 'IP Address', 18),
            ('prefix', 'Prefix', 18),
        ],
        ipv6_rows,
        width,
    )
    print()


def print_interface(interface, width):
    """Render a single interface block."""
    if width < WIDE_THRESHOLD:
        print_interface_compact(interface, width)
    else:
        print_interface_wide(interface, width)


def print_summary(interfaces, width):
    """Print an all-interface summary table."""
    rows = []
    lower_width = 20 if width < WIDE_THRESHOLD else 28
    name_width = 18 if width < WIDE_THRESHOLD else 22
    type_width = 10 if width < WIDE_THRESHOLD else 12
    for interface in interfaces:
        lower_layers = ','.join(interface['lower_layers']) if interface['lower_layers'] else '-'
        rows.append({
            'id': str(interface['id']),
            'name': fit_display(interface['name'], name_width),
            'en': format_enable(interface['enable']),
            'status': interface['status'],
            'type': fit_display(interface['type'], type_width),
            'lower': fit_display(lower_layers, lower_width),
            'ipv4': f'{format_enable(interface["ipv4_enable"])} {interface["ipv4_count"]}',
            'ipv6': f'{format_enable(interface["ipv6_enable"])} {interface["ipv6_count"]}',
        })

    lines = ['  IP INTERFACE SUMMARY']
    lines.extend(render_table(
        [
            ('id', 'ID', 2),
            ('name', 'Name/Alias', name_width),
            ('en', 'En', 2),
            ('status', 'Status', 8),
            ('type', 'Type', type_width),
            ('lower', 'LowerLayers', lower_width),
            ('ipv4', 'IPv4', 4),
            ('ipv6', 'IPv6', 4),
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

    print_ip_overview(dm, width)

    interfaces = discover_interfaces(dm)
    if not interfaces:
        print('No IP interfaces found.')
        return

    for interface in interfaces:
        print_interface(interface, width)

    print_summary(interfaces, width)


if __name__ == '__main__':
    try:
        main()
    except BrokenPipeError:
        try:
            sys.stdout.close()
        finally:
            raise SystemExit(0)
