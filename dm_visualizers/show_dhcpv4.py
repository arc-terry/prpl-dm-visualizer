#!/usr/bin/env python3
"""
Parse DM.txt and display TR-181 Device.DHCPv4 clients and server pools
as a text-based visualized diagram.

Usage: python3 dm_visualizers/show_dhcpv4.py [DM.txt]

References:
  - Broadband Forum TR-181 Device:2 Data Model (Device.DHCPv4)
  - prpl Foundation tr181-dhcp plugin
    https://gitlab.com/prpl-foundation/components/core/plugins/tr181-dhcp
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


def normalize_ref(value):
    if not value:
        return ''
    return value.strip().strip('"').rstrip('.')


def format_enable(value):
    return '🟢' if value == '1' else '🔴'


def discover_clients(dm):
    pat = re.compile(r'^Device\.DHCPv4\.Client\.(\d+)\.(Alias|Status)$')
    ids = set()
    for key in dm:
        m = pat.match(key)
        if m:
            ids.add(int(m.group(1)))
    rows = []
    for cid in sorted(ids):
        prefix = f'Device.DHCPv4.Client.{cid}'
        rows.append({
            'id': cid,
            'alias': nonempty(get_attr(dm, prefix, 'Alias')),
            'enable': get_attr(dm, prefix, 'Enable') or '0',
            'status': nonempty(get_attr(dm, prefix, 'Status')),
            'dhcp_status': nonempty(get_attr(dm, prefix, 'DHCPStatus')),
            'iface': nonempty(normalize_ref(get_attr(dm, prefix, 'Interface'))),
            'ip': nonempty(get_attr(dm, prefix, 'IPAddress')),
            'mask': nonempty(get_attr(dm, prefix, 'SubnetMask')),
            'server': nonempty(get_attr(dm, prefix, 'DHCPServer')),
            'routers': nonempty(get_attr(dm, prefix, 'IPRouters')),
            'dns': nonempty(get_attr(dm, prefix, 'DNSServers')),
            'lease': nonempty(get_attr(dm, prefix, 'LeaseTimeRemaining')),
        })
    return rows


def discover_pools(dm):
    pat = re.compile(r'^Device\.DHCPv4\.Server\.Pool\.(\d+)\.(Alias|Status)$')
    ids = set()
    for key in dm:
        m = pat.match(key)
        if m:
            ids.add(int(m.group(1)))
    rows = []
    for pid in sorted(ids):
        prefix = f'Device.DHCPv4.Server.Pool.{pid}'
        rows.append({
            'id': pid,
            'alias': nonempty(get_attr(dm, prefix, 'Alias')),
            'enable': get_attr(dm, prefix, 'Enable') or '0',
            'status': nonempty(get_attr(dm, prefix, 'Status')),
            'order': nonempty(get_attr(dm, prefix, 'Order')),
            'iface': nonempty(normalize_ref(get_attr(dm, prefix, 'Interface'))),
            'range': f'{nonempty(get_attr(dm, prefix, "MinAddress"))}..{nonempty(get_attr(dm, prefix, "MaxAddress"))}',
            'mask': nonempty(get_attr(dm, prefix, 'SubnetMask')),
            'routers': nonempty(get_attr(dm, prefix, 'IPRouters')),
            'dns': nonempty(get_attr(dm, prefix, 'DNSServers')),
            'domain': nonempty(get_attr(dm, prefix, 'DomainName')),
            'lease': nonempty(get_attr(dm, prefix, 'LeaseTime')),
        })
    return rows


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
    print()


def print_line_box(title, lines, width):
    content_w = max(width - 4, 16)
    box_lines = [title]
    if lines:
        box_lines.extend(fit_display(line, content_w).rstrip() for line in lines)
    else:
        box_lines.append('(none)')
    box_w = box_width(width, box_lines)
    print(hline('─', box_w, '┌', '┐'))
    print(boxline(box_lines[0], box_w))
    print(hline('─', box_w, '├', '┤'))
    for line in box_lines[1:]:
        print(boxline(line, box_w))
    print(hline('─', box_w, '└', '┘'))
    print()


def print_overview(dm, clients, pools, width):
    lines = [
        f'Clients: {len(clients)} / {nonempty(get_attr(dm, "Device.DHCPv4", "ClientNumberOfEntries"))}',
        f'Server: {format_enable(get_attr(dm, "Device.DHCPv4.Server", "Enable") or "0")}  Pools: {len(pools)} / {nonempty(get_attr(dm, "Device.DHCPv4.Server", "PoolNumberOfEntries"))}',
    ]
    box_w = box_width(width, lines, title='TR-181 DHCPV4 OVERVIEW')
    print(hline('═', box_w, '╔', '╗'))
    print(f'║{"TR-181 DHCPV4 OVERVIEW":^{box_w - 2}}║')
    print(hline('═', box_w, '╠', '╣'))
    for line in lines:
        print(boxline(line, box_w))
    print(hline('═', box_w, '╚', '╝'))
    print()


def print_compact(clients, pools, width):
    client_lines = []
    for row in clients:
        client_lines.append(
            f'#{row["id"]} {row["alias"]}  {format_enable(row["enable"])} {row["status"]}  '
            f'{row["dhcp_status"]}  if={row["iface"]}'
        )
        client_lines.append(f'  ip={row["ip"]}/{row["mask"]} gw={row["routers"]} dns={row["dns"]} lease={row["lease"]}')
    print_line_box('Clients', client_lines, width)

    pool_lines = []
    for row in pools:
        pool_lines.append(
            f'#{row["order"]} {row["alias"]}  {format_enable(row["enable"])} {row["status"]}  '
            f'if={row["iface"]}'
        )
        pool_lines.append(f'  range={row["range"]} mask={row["mask"]} gw={row["routers"]} dns={row["dns"]}')
    print_line_box('Server Pools', pool_lines, width)


def print_wide(clients, pools, width):
    client_rows = []
    for row in clients:
        client_rows.append({
            'id': str(row['id']),
            'alias': row['alias'],
            'en': format_enable(row['enable']),
            'status': row['status'],
            'dhcp': row['dhcp_status'],
            'iface': row['iface'],
            'ip': row['ip'],
            'server': row['server'],
        })
    print_subtable(
        'Clients',
        [
            ('id', '#', 2),
            ('alias', 'Alias', 10),
            ('en', 'En', 2),
            ('status', 'Status', 8),
            ('dhcp', 'DHCP', 7),
            ('iface', 'Interface', 16),
            ('ip', 'IP', 15),
            ('server', 'Server', 12),
        ],
        client_rows,
        width,
    )

    pool_rows = []
    for row in pools:
        pool_rows.append({
            'order': row['order'],
            'alias': row['alias'],
            'en': format_enable(row['enable']),
            'status': row['status'],
            'iface': row['iface'],
            'range': row['range'],
            'mask': row['mask'],
            'dns': row['dns'],
        })
    print_subtable(
        'Server Pools',
        [
            ('order', 'Ord', 3),
            ('alias', 'Alias', 12),
            ('en', 'En', 2),
            ('status', 'Status', 8),
            ('iface', 'Interface', 16),
            ('range', 'Range', 20),
            ('mask', 'Mask', 15),
            ('dns', 'DNS', 15),
        ],
        pool_rows,
        width,
    )


def print_summary(clients, pools, width):
    alias_w = 12 if width < WIDE_THRESHOLD else 14
    iface_w = 16 if width < WIDE_THRESHOLD else 20

    client_lines = ['  DHCPV4 CLIENT SUMMARY']
    client_lines.extend(render_table(
        [
            ('alias', 'Alias', alias_w),
            ('iface', 'Interface', iface_w),
            ('ip', 'IP', 15),
            ('status', 'Status', 8),
        ],
        [
            {
                'alias': fit_display(row['alias'], alias_w),
                'iface': fit_display(row['iface'], iface_w),
                'ip': row['ip'],
                'status': row['dhcp_status'],
            }
            for row in clients
        ],
    ))
    total_w = max(width, max(display_width(line) for line in client_lines))
    print(hline('═', total_w))
    print(client_lines[0])
    print(hline('═', total_w))
    for line in client_lines[1:]:
        print(line)
    print()

    pool_lines = ['  DHCPV4 POOL SUMMARY']
    pool_lines.extend(render_table(
        [
            ('alias', 'Alias', alias_w),
            ('iface', 'Interface', iface_w),
            ('range', 'Range', 20),
            ('status', 'Status', 8),
        ],
        [
            {
                'alias': fit_display(row['alias'], alias_w),
                'iface': fit_display(row['iface'], iface_w),
                'range': row['range'],
                'status': row['status'],
            }
            for row in pools
        ],
    ))
    total_w = max(width, max(display_width(line) for line in pool_lines))
    print(hline('═', total_w))
    print(pool_lines[0])
    print(hline('═', total_w))
    for line in pool_lines[1:]:
        print(line)
    print()


def main():
    filepath = sys.argv[1] if len(sys.argv) > 1 else 'DM.txt'
    width = warn_narrow_width()
    print(f'Parsing: {filepath}')
    print()
    dm = parse_dm(filepath)
    clients = discover_clients(dm)
    pools = discover_pools(dm)
    print_overview(dm, clients, pools, width)
    if width < WIDE_THRESHOLD:
        print_compact(clients, pools, width)
    else:
        print_wide(clients, pools, width)
    print_summary(clients, pools, width)


if __name__ == '__main__':
    main()
