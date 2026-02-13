#!/usr/bin/env python3
"""
Parse DM.txt and display TR-181 Device.Firewall chains and rules
as a text-based visualized diagram.

Usage: python3 dm_visualizers/show_firewall_rules.py [DM.txt]

References:
  - Broadband Forum TR-181 Device:2 Data Model (Device.Firewall.Chain.{i}.Rule.{i})
  - prpl Foundation tr181-firewall plugin
    https://gitlab.com/prpl-foundation/components/core/plugins/tr181-firewall
"""

import os
import re
import sys
from collections import defaultdict

from utils import (
    get_term_width, parse_dm, get_attr, warn_narrow_width,
    display_width, pad_display, hline, boxline, box_width,
)

PROTO_MAP = {
    '6': 'TCP',
    '17': 'UDP',
    '1': 'ICMP',
    '58': 'ICMPv6',
    '-1': 'any',
}





def discover_chains(dm):
    """Find all firewall chain IDs and their metadata."""
    chain_re = re.compile(r'^Device\.Firewall\.Chain\.(\d+)\.Name$')
    chains = {}
    for key in dm:
        m = chain_re.match(key)
        if m:
            cid = int(m.group(1))
            prefix = f'Device.Firewall.Chain.{cid}'
            chains[cid] = {
                'name': dm[key],
                'alias': get_attr(dm, prefix, 'Alias') or '',
                'enable': get_attr(dm, prefix, 'Enable') or '0',
                'rule_count': int(get_attr(dm, prefix, 'RuleNumberOfEntries') or '0'),
            }
    return chains


def discover_rules(dm, chain_id):
    """Find all rule IDs for a given chain."""
    rule_re = re.compile(
        rf'^Device\.Firewall\.Chain\.{chain_id}\.Rule\.(\d+)\.Alias$'
    )
    rules = {}
    for key in dm:
        m = rule_re.match(key)
        if m:
            rid = int(m.group(1))
            prefix = f'Device.Firewall.Chain.{chain_id}.Rule.{rid}'
            order = get_attr(dm, prefix, 'Order') or str(rid)

            proto_raw = get_attr(dm, prefix, 'Protocol') or '-1'
            proto = PROTO_MAP.get(proto_raw, f'proto:{proto_raw}')

            dest_port = get_attr(dm, prefix, 'DestPort') or '-1'
            dest_port_max = get_attr(dm, prefix, 'DestPortRangeMax') or '-1'
            src_port = get_attr(dm, prefix, 'SourcePort') or '-1'
            src_ip = get_attr(dm, prefix, 'SourceIP') or ''
            dest_ip = get_attr(dm, prefix, 'DestIP') or ''
            conn_state = get_attr(dm, prefix, 'ConnectionState') or ''

            # Build port display
            if dest_port != '-1':
                port_str = str(dest_port)
                if dest_port_max != '-1':
                    port_str += f'-{dest_port_max}'
            else:
                port_str = '*'

            if src_port != '-1':
                src_port_str = str(src_port)
            else:
                src_port_str = '*'

            rules[rid] = {
                'alias': dm[key],
                'order': int(order),
                'enable': get_attr(dm, prefix, 'Enable') or '0',
                'status': get_attr(dm, prefix, 'Status') or '',
                'target': get_attr(dm, prefix, 'Target') or '',
                'protocol': proto,
                'dest_port': port_str,
                'src_port': src_port_str,
                'src_ip': src_ip or '*',
                'dest_ip': dest_ip or '*',
                'conn_state': conn_state,
                'ip_version': get_attr(dm, prefix, 'IPVersion') or '-1',
            }
    return rules


def format_target(target):
    """Return styled target string."""
    t = target.lower()
    if t in ('accept',):
        return f'✅ {target}'
    elif t in ('drop',):
        return f'🚫 {target}'
    elif t in ('reject',):
        return f'❌ {target}'
    return f'➡️  {target}'





def print_firewall_overview(dm, width):
    """Print high-level firewall settings."""
    enable = get_attr(dm, 'Device.Firewall', 'Enable') or '?'
    fw_type = get_attr(dm, 'Device.Firewall', 'Type') or '?'
    config = get_attr(dm, 'Device.Firewall', 'Config') or '?'
    policy = get_attr(dm, 'Device.Firewall', 'PolicyLevel') or '?'
    chain_count = get_attr(dm, 'Device.Firewall', 'ChainNumberOfEntries') or '?'

    lines = [
        f'Enable: {enable}  Type: {fw_type}  Config: {config}',
        f'Policy: {policy}',
        f'Chains: {chain_count}',
    ]
    box_w = box_width(width, lines, title='TR-181 FIREWALL OVERVIEW')
    print(hline('═', box_w, '╔', '╗'))
    title = 'TR-181 FIREWALL OVERVIEW'
    print(f'║{title:^{box_w - 2}}║')
    print(hline('═', box_w, '╠', '╣'))
    for line in lines:
        print(boxline(line, box_w))
    print(hline('═', box_w, '╚', '╝'))
    print()


def print_chain_compact(chain_id, chain_info, rules, width):
    """Print chain and rules in compact card layout for narrow terminals."""
    enable = '🟢' if chain_info['enable'] == '1' else '🔴'
    header = f'{enable} Chain {chain_id}: {chain_info["name"]} ({chain_info["alias"]})'
    lines = [header, f'Rules: {chain_info["rule_count"]}']
    if not rules:
        lines.append('(no rules)')
    else:
        sorted_rules = sorted(rules.values(), key=lambda r: r['order'])
        for r in sorted_rules:
            target_str = format_target(r['target'])
            line1 = f'#{r["order"]} {r["alias"]}  {target_str}  {r["protocol"]}'
            parts = []
            if r['dest_port'] != '*':
                parts.append(f'dst:{r["dest_port"]}')
            if r['src_port'] != '*':
                parts.append(f'src:{r["src_port"]}')
            if r['src_ip'] != '*':
                parts.append(f'from:{r["src_ip"]}')
            if r['dest_ip'] != '*':
                parts.append(f'to:{r["dest_ip"]}')
            if r['conn_state']:
                parts.append(f'state:{r["conn_state"]}')
            if parts:
                line1 += '  ' + ' '.join(parts)
            lines.append(line1)

    box_w = box_width(width, lines)
    print(hline('─', box_w, '┌', '┐'))
    print(boxline(lines[0], box_w))
    print(boxline(lines[1], box_w))
    print(hline('─', box_w, '├', '┤'))
    for line in lines[2:]:
        print(boxline(line, box_w))
    print(hline('─', box_w, '└', '┘'))
    print()


def print_chain_wide(chain_id, chain_info, rules, width):
    """Print chain and rules in table layout for wide terminals."""
    enable = '🟢' if chain_info['enable'] == '1' else '🔴'

    # Compute column widths based on available space
    # Fixed overhead: "│  " prefix = 3 chars, spaces between cols
    # Columns: #, Alias, Target, Proto, DstPort, SrcPort, SrcIP, DstIP, Extra
    avail = width - 4  # "│  " + trailing space
    # Minimum widths
    c_order = 4
    c_proto = 7
    c_dport = 7
    c_sport = 7
    fixed = c_order + c_proto + c_dport + c_sport + 4  # 4 spaces between
    remaining = avail - fixed
    # Distribute remaining among alias, target, src_ip, dest_ip
    c_alias = max(8, min(16, remaining // 4))
    c_target = max(8, min(14, remaining // 4))
    c_sip = max(4, min(16, remaining // 4))
    c_dip = max(4, remaining - c_alias - c_target - c_sip)

    header = f'{enable} Chain {chain_id}: {chain_info["name"]} ({chain_info["alias"]})'
    lines = [header, f'Rules: {chain_info["rule_count"]}']
    if not rules:
        lines.append('(no rules)')
    else:
        sorted_rules = sorted(rules.values(), key=lambda r: r['order'])
        rows = []
        for r in sorted_rules:
            target_str = format_target(r['target'])
            extra = f'state:{r["conn_state"]}' if r['conn_state'] else ''
            rows.append({
                'order': str(r['order']),
                'alias': r['alias'],
                'target': target_str,
                'proto': r['protocol'],
                'dport': r['dest_port'],
                'sport': r['src_port'],
                'src_ip': r['src_ip'],
                'dst_ip': r['dest_ip'],
                'extra': extra,
            })

        has_extra = any(row['extra'] for row in rows)
        columns = [
            ('order', '#'),
            ('alias', 'Alias'),
            ('target', 'Target'),
            ('proto', 'Proto'),
            ('dport', 'DPort'),
            ('sport', 'SPort'),
            ('src_ip', 'SrcIP'),
            ('dst_ip', 'DstIP'),
        ]
        if has_extra:
            columns.append(('extra', 'Extra'))

        min_widths = {
            'order': 4,
            'alias': 8,
            'target': 8,
            'proto': 7,
            'dport': 7,
            'sport': 7,
            'src_ip': 8,
            'dst_ip': 8,
            'extra': 12,
        }
        widths = {}
        for key, label in columns:
            widths[key] = max(min_widths.get(key, 0), display_width(label),
                              max(display_width(row[key]) for row in rows))

        header_row = {key: label for key, label in columns}
        hdr = ' '.join(pad_display(header_row[key], widths[key]) for key, _ in columns)
        sep = ' '.join('─' * widths[key] for key, _ in columns)
        lines.extend([hdr, sep])

        for row in rows:
            line = ' '.join(pad_display(row[key], widths[key]) for key, _ in columns)
            lines.append(line)

    box_w = box_width(width, lines)
    print(hline('─', box_w, '┌', '┐'))
    print(boxline(lines[0], box_w))
    print(boxline(lines[1], box_w))
    print(hline('─', box_w, '├', '┤'))
    for idx, line in enumerate(lines[2:], start=2):
        if idx == 3:
            print(boxline(line, box_w, fill='─'))
        else:
            print(boxline(line, box_w))
    print(hline('─', box_w, '└', '┘'))
    print()


def print_chain(chain_id, chain_info, rules, width):
    """Dispatch to compact or wide layout based on terminal width."""
    if width < 90:
        print_chain_compact(chain_id, chain_info, rules, width)
    else:
        print_chain_wide(chain_id, chain_info, rules, width)


def main():
    filepath = sys.argv[1] if len(sys.argv) > 1 else 'DM.txt'
    width = warn_narrow_width()

    print(f'Parsing: {filepath}')
    print()
    dm = parse_dm(filepath)

    print_firewall_overview(dm, width)

    chains = discover_chains(dm)
    if not chains:
        print('No firewall chains found.')
        return

    for cid in sorted(chains.keys()):
        rules = discover_rules(dm, cid)
        print_chain(cid, chains[cid], rules, width)

    # Summary table
    summary_lines = ['  CHAIN SUMMARY']
    # Adapt summary columns to width
    if width >= 70:
        c_id, c_name, c_alias, c_en, c_rules = 4, 26, 16, 4, 6
    else:
        c_id, c_name, c_alias, c_en, c_rules = 3, 18, 12, 3, 5
    header = f'  {"ID":<{c_id}} {"Name":<{c_name}} {"Alias":<{c_alias}} {"En":<{c_en}} {"Rules":<{c_rules}}'
    separator = f'  {"─"*c_id} {"─"*c_name} {"─"*c_alias} {"─"*c_en} {"─"*c_rules}'
    summary_lines.extend([header, separator])
    for cid in sorted(chains.keys()):
        c = chains[cid]
        en = '🟢' if c['enable'] == '1' else '🔴'
        summary_lines.append(
            f'  {cid:<{c_id}} {c["name"]:<{c_name}} {c["alias"]:<{c_alias}} '
            f'{en:<{c_en}} {c["rule_count"]:<{c_rules}}'
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
