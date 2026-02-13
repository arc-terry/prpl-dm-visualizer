#!/usr/bin/env python3
"""
Parse DM.txt and display TR-181 X_PRPLWARE-COM_WANManager WAN modes
and their interfaces as a text-based diagram.

Usage: python3 dm_visualizers/show_wan_manager.py [DM.txt]

References:
  - Broadband Forum TR-181 Device:2 Data Model
  - prpl Foundation wan-manager plugin
    https://gitlab.com/prpl-foundation/components/core/plugins/wan-manager
"""

import re
import sys

from utils import (
    get_attr, parse_dm, warn_narrow_width,
    display_width, pad_display, fit_display,
    hline, boxline, box_width,
)

WM_PREFIX = 'Device.X_PRPLWARE-COM_WANManager'





def resolve_alias(dm, ref):
    """Resolve a Device.* reference to its Alias or Name."""
    if not ref:
        return ''
    path = ref.rstrip('.')
    alias = get_attr(dm, path, 'Alias') or get_attr(dm, path, 'Name') or ''
    return alias


def ref_label(dm, ref):
    """Return 'Short.Path (alias)' or 'Short.Path' for a reference."""
    short = shorten_ref(ref)
    if short == '-':
        return '-'
    alias = resolve_alias(dm, ref)
    if alias:
        return f'{short} ({alias})'
    return short







def shorten_ref(ref):
    """Shorten a Device.* reference for display."""
    if not ref:
        return '-'
    return ref.replace('Device.', '').rstrip('.')


def discover_wan_modes(dm):
    """Find all WANManager.WAN.{i} instances."""
    wan_re = re.compile(rf'^{re.escape(WM_PREFIX)}\.WAN\.(\d+)\.Alias$')
    modes = {}
    for key in dm:
        m = wan_re.match(key)
        if m:
            wid = int(m.group(1))
            prefix = f'{WM_PREFIX}.WAN.{wid}'
            modes[wid] = {
                'alias': dm[key],
                'status': get_attr(dm, prefix, 'Status') or '?',
                'phys_type': get_attr(dm, prefix, 'PhysicalType') or '?',
                'phys_ref': get_attr(dm, prefix, 'PhysicalReference') or '',
                'dns_mode': get_attr(dm, prefix, 'DNSMode') or '?',
                'ipv6_dns': get_attr(dm, prefix, 'IPv6DNSMode') or '?',
                'sensing': get_attr(dm, prefix, 'EnableSensing') or '0',
                'sensing_pri': get_attr(dm, prefix, 'SensingPriority') or '0',
                'sfp_type': get_attr(dm, prefix, 'SFPType') or '',
                'origin': get_attr(dm, prefix, 'Origin') or '',
            }
    return modes


def discover_intfs(dm, wan_id):
    """Find all WANManager.WAN.{wan_id}.Intf.{j} instances."""
    intf_re = re.compile(
        rf'^{re.escape(WM_PREFIX)}\.WAN\.{wan_id}\.Intf\.(\d+)\.Alias$'
    )
    intfs = {}
    for key in dm:
        m = intf_re.match(key)
        if m:
            iid = int(m.group(1))
            prefix = f'{WM_PREFIX}.WAN.{wan_id}.Intf.{iid}'
            intfs[iid] = {
                'alias': dm[key],
                'name': get_attr(dm, prefix, 'Name') or '',
                'ipv4_mode': get_attr(dm, prefix, 'IPv4Mode') or '-',
                'ipv6_mode': get_attr(dm, prefix, 'IPv6Mode') or '-',
                'ipv4_ref': get_attr(dm, prefix, 'IPv4Reference') or '',
                'ipv6_ref': get_attr(dm, prefix, 'IPv6Reference') or '',
                'dhcpv4_ref': get_attr(dm, prefix, 'DHCPv4Reference') or '',
                'dhcpv6_ref': get_attr(dm, prefix, 'DHCPv6Reference') or '',
                'type': get_attr(dm, prefix, 'Type') or '-',
                'vlan_id': get_attr(dm, prefix, 'VlanID') or '-',
                'default_route': get_attr(dm, prefix, 'DefaultRouteReference') or '',
                'bridge_ref': get_attr(dm, prefix, 'BridgeReference') or '',
                'pppv4_ref': get_attr(dm, prefix, 'PPPv4Reference') or '',
                'pppv6_ref': get_attr(dm, prefix, 'PPPv6Reference') or '',
            }
    return intfs


def print_overview(dm, width):
    """Print WANManager global settings."""
    op_mode = get_attr(dm, WM_PREFIX, 'OperationMode') or '?'
    sensing_pol = get_attr(dm, WM_PREFIX, 'SensingPolicy') or '?'
    sensing_to = get_attr(dm, WM_PREFIX, 'SensingTimeout') or '?'
    wan_mode = get_attr(dm, WM_PREFIX, 'WANMode') or '?'

    lines = [
        (f'OperationMode: {op_mode}   SensingPolicy: {sensing_pol}   '
         f'SensingTimeout: {sensing_to}s'),
        f'Active WANMode: {wan_mode}',
    ]
    box_w = box_width(width, lines, title='WAN MANAGER OVERVIEW')
    print(hline('═', box_w, '╔', '╗'))
    title = 'WAN MANAGER OVERVIEW'
    print(f'║{title:^{box_w - 2}}║')
    print(hline('═', box_w, '╠', '╣'))
    for line in lines:
        print(boxline(line, box_w))
    print(hline('═', box_w, '╚', '╝'))
    print()


def print_wan_compact(dm, wan_id, mode, intfs, width, is_active):
    """Print WAN mode in compact card layout."""
    st = '🟢' if mode['status'] != 'Disabled' else '🔴'
    sense = '📡' if mode['sensing'] == '1' else '  '
    active = ' ★ ACTIVE' if is_active else ''
    top_lines = [
        f'{st} WAN.{wan_id}: {mode["alias"]}{active}',
        (f'Physical: {mode["phys_type"]}  Ref: {shorten_ref(mode["phys_ref"])}  '
         f'{sense} Sensing'),
        f'DNS: {mode["dns_mode"]}  IPv6DNS: {mode["ipv6_dns"]}  Status: {mode["status"]}',
    ]
    body_lines = []
    if not intfs:
        body_lines.append('(no interfaces)')
    else:
        for iid in sorted(intfs.keys()):
            intf = intfs[iid]
            line = (f'Intf.{iid} "{intf["alias"]}"  '
                    f'IPv4:{intf["ipv4_mode"]}  IPv6:{intf["ipv6_mode"]}  '
                    f'{intf["type"]}')
            if intf['type'] == 'vlan':
                line += f' vlan:{intf["vlan_id"]}'
            body_lines.append(line)
            refs = []
            if intf['ipv4_ref']:
                refs.append(f'IPv4→{ref_label(dm, intf["ipv4_ref"])}')
            if intf['dhcpv4_ref']:
                refs.append(f'DHCPv4→{ref_label(dm, intf["dhcpv4_ref"])}')
            if intf['dhcpv6_ref']:
                refs.append(f'DHCPv6→{ref_label(dm, intf["dhcpv6_ref"])}')
            if intf['default_route']:
                refs.append(f'Route→{ref_label(dm, intf["default_route"])}')
            if refs:
                body_lines.append(f'  {" | ".join(refs)}')

    box_w = box_width(width, top_lines + body_lines)
    print(hline('─', box_w, '┌', '┐'))
    for line in top_lines:
        print(boxline(line, box_w))
    print(hline('─', box_w, '├', '┤'))
    for line in body_lines:
        print(boxline(line, box_w))
    print(hline('─', box_w, '└', '┘'))
    print()


def print_wan_wide(dm, wan_id, mode, intfs, width, is_active):
    """Print WAN mode in wide table layout."""
    st = '🟢' if mode['status'] != 'Disabled' else '🔴'
    sense = '📡' if mode['sensing'] == '1' else '  '
    active = ' ★ ACTIVE' if is_active else ''
    top_lines = [
        f'{st} WAN.{wan_id}: {mode["alias"]}{active}',
        (f'Physical: {mode["phys_type"]}  Ref: {shorten_ref(mode["phys_ref"])}  '
         f'{sense} Sensing  Status: {mode["status"]}  DNS: {mode["dns_mode"]}  '
         f'IPv6DNS: {mode["ipv6_dns"]}'),
    ]
    body_lines = []
    if not intfs:
        body_lines.append('(no interfaces)')
    else:
        c_id = 6
        c_alias = 10
        c_v4mode = 10
        c_v6mode = 10
        c_type = 10
        c_vlan = 6
        c_v4ref = 28
        c_route = max(10, width - c_id - c_alias - c_v4mode - c_v6mode - c_type - c_vlan - c_v4ref - 12)

        hdr = (f'{"Intf":<{c_id}} {"Alias":<{c_alias}} {"IPv4Mode":<{c_v4mode}} '
               f'{"IPv6Mode":<{c_v6mode}} {"Type":<{c_type}} {"VLAN":<{c_vlan}} '
               f'{"IPv4Ref":<{c_v4ref}} {"DefRoute":<{c_route}}')
        sep = (f'{"─"*c_id} {"─"*c_alias} {"─"*c_v4mode} '
               f'{"─"*c_v6mode} {"─"*c_type} {"─"*c_vlan} '
               f'{"─"*c_v4ref} {"─"*c_route}')
        body_lines.extend([hdr, sep])

        for iid in sorted(intfs.keys()):
            intf = intfs[iid]
            vlan = intf['vlan_id'] if intf['type'] == 'vlan' else '-'
            line = (f'{iid:<{c_id}} {intf["alias"]:<{c_alias}} '
                    f'{intf["ipv4_mode"]:<{c_v4mode}} '
                    f'{intf["ipv6_mode"]:<{c_v6mode}} '
                    f'{intf["type"]:<{c_type}} {vlan:<{c_vlan}} '
                    f'{ref_label(dm, intf["ipv4_ref"]):<{c_v4ref}} '
                    f'{ref_label(dm, intf["default_route"]):<{c_route}}')
            body_lines.append(line)

    box_w = box_width(width, top_lines + body_lines)
    print(hline('─', box_w, '┌', '┐'))
    for line in top_lines:
        print(boxline(line, box_w))
    print(hline('─', box_w, '├', '┤'))
    for line in body_lines:
        print(boxline(line, box_w))
    print(hline('─', box_w, '└', '┘'))
    print()


def print_wan_mode(dm, wan_id, mode, intfs, width, is_active):
    if width < 90:
        print_wan_compact(dm, wan_id, mode, intfs, width, is_active)
    else:
        print_wan_wide(dm, wan_id, mode, intfs, width, is_active)


def main():
    filepath = sys.argv[1] if len(sys.argv) > 1 else 'DM.txt'
    width = warn_narrow_width()

    print(f'Parsing: {filepath}')
    print()
    dm = parse_dm(filepath)

    print_overview(dm, width)

    modes = discover_wan_modes(dm)
    if not modes:
        print('No WANManager WAN modes found.')
        return

    active_mode = get_attr(dm, WM_PREFIX, 'WANMode') or ''

    for wid in sorted(modes.keys()):
        intfs = discover_intfs(dm, wid)
        is_active = (modes[wid]['alias'] == active_mode)
        print_wan_mode(dm, wid, modes[wid], intfs, width, is_active)

    # Summary table
    summary_lines = ['  WAN MODE SUMMARY']
    if width >= 90:
        c = (4, 20, 10, 10, 10, 5, 6)
        headers = ('ID', 'Alias', 'PhysType', 'Status', 'DNS', 'Sens', 'Intfs')
    else:
        c = (3, 16, 9, 9, 4, 4)
        headers = ('ID', 'Alias', 'Phys', 'Status', 'Sn', 'If')
    header = '  ' + ' '.join(fit_display(label, width) for label, width in zip(headers, c))
    separator = '  ' + ' '.join('─' * width for width in c)
    summary_lines.extend([header, separator])

    for wid in sorted(modes.keys()):
        m = modes[wid]
        intfs = discover_intfs(dm, wid)
        st = '🟢' if m['status'] != 'Disabled' else '🔴'
        sense = '📡' if m['sensing'] == '1' else '  '
        active = '★' if m['alias'] == active_mode else ' '
        if width >= 90:
            values = (
                f'{active}{wid}',
                m['alias'],
                m['phys_type'],
                f'{st} {m["status"]}',
                m['dns_mode'],
                sense,
                str(len(intfs)),
            )
        else:
            values = (
                f'{active}{wid}',
                m['alias'],
                m['phys_type'],
                st,
                sense,
                str(len(intfs)),
            )
        summary_lines.append(
            ' ' + ' '.join(fit_display(value, width) for value, width in zip(values, c))
        )
    summary_width = max(width, max(display_width(line) for line in summary_lines))
    print(hline('═', summary_width))
    print(summary_lines[0])
    print(hline('═', summary_width))
    for line in summary_lines[1:]:
        print(line)
    print()


if __name__ == '__main__':
    main()
