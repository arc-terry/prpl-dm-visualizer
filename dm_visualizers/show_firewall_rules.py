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
import shutil
import sys
from collections import defaultdict

PROTO_MAP = {
    '6': 'TCP',
    '17': 'UDP',
    '1': 'ICMP',
    '58': 'ICMPv6',
    '-1': 'any',
}


def get_term_width():
    """Return terminal width, defaulting to 80."""
    try:
        return shutil.get_terminal_size((80, 24)).columns
    except Exception:
        return 80


def parse_dm(filepath):
    """Parse DM.txt into a dict of {path: value}."""
    dm = {}
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            m = re.match(r'^(Device\..+?)=(.*)$', line)
            if m:
                key = m.group(1)
                val = m.group(2).strip('"')
                dm[key] = val
    return dm


def get_attr(dm, prefix, attr):
    """Get attribute from DM dict, trying with/without double dot."""
    for key in [f"{prefix}.{attr}", f"{prefix}..{attr}"]:
        if key in dm:
            return dm[key]
    return None


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


def hline(char, width, left='', right=''):
    """Draw a horizontal line fitting the terminal width."""
    inner = width - len(left) - len(right)
    return f'{left}{char * inner}{right}'


def boxline(text, width, pad=2):
    """Render a left-aligned text line inside a box of given width."""
    inner = width - 2  # subtract │ on each side
    return f'│{" " * pad}{text}'


def print_firewall_overview(dm, width):
    """Print high-level firewall settings."""
    enable = get_attr(dm, 'Device.Firewall', 'Enable') or '?'
    fw_type = get_attr(dm, 'Device.Firewall', 'Type') or '?'
    config = get_attr(dm, 'Device.Firewall', 'Config') or '?'
    policy = get_attr(dm, 'Device.Firewall', 'PolicyLevel') or '?'
    chain_count = get_attr(dm, 'Device.Firewall', 'ChainNumberOfEntries') or '?'

    print(hline('═', width, '╔', '╗'))
    title = 'TR-181 FIREWALL OVERVIEW'
    print(f'║{title:^{width - 2}}║')
    print(hline('═', width, '╠', '╣'))
    print(boxline(f'Enable: {enable}  Type: {fw_type}  Config: {config}', width))
    print(boxline(f'Policy: {policy}', width))
    print(boxline(f'Chains: {chain_count}', width))
    print(hline('═', width, '╚', '╝'))
    print()


def print_chain_compact(chain_id, chain_info, rules, width):
    """Print chain and rules in compact card layout for narrow terminals."""
    enable = '🟢' if chain_info['enable'] == '1' else '🔴'

    print(hline('─', width, '┌', '┐'))
    print(boxline(f'{enable} Chain {chain_id}: {chain_info["name"]} ({chain_info["alias"]})', width))
    print(boxline(f'Rules: {chain_info["rule_count"]}', width))
    print(hline('─', width, '├', '┤'))

    if not rules:
        print(boxline('(no rules)', width))
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
            print(boxline(line1, width))

    print(hline('─', width, '└', '┘'))
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

    print(hline('─', width, '┌', '┐'))
    print(boxline(f'{enable} Chain {chain_id}: {chain_info["name"]} ({chain_info["alias"]})', width))
    print(boxline(f'Rules: {chain_info["rule_count"]}', width))
    print(hline('─', width, '├', '┤'))

    if not rules:
        print(boxline('(no rules)', width))
    else:
        hdr = (f'{"#":<{c_order}} {"Alias":<{c_alias}} {"Target":<{c_target}} '
               f'{"Proto":<{c_proto}} {"DPort":<{c_dport}} {"SPort":<{c_sport}} '
               f'{"SrcIP":<{c_sip}} {"DstIP":<{c_dip}}')
        sep = (f'{"─"*c_order} {"─"*c_alias} {"─"*c_target} '
               f'{"─"*c_proto} {"─"*c_dport} {"─"*c_sport} '
               f'{"─"*c_sip} {"─"*c_dip}')
        print(boxline(hdr, width))
        print(boxline(sep, width))

        sorted_rules = sorted(rules.values(), key=lambda r: r['order'])
        for r in sorted_rules:
            target_str = format_target(r['target'])
            extra = ''
            if r['conn_state']:
                extra = f' state:{r["conn_state"]}'
            line = (f'{r["order"]:<{c_order}} {r["alias"]:<{c_alias}} {target_str:<{c_target}} '
                    f'{r["protocol"]:<{c_proto}} {r["dest_port"]:<{c_dport}} {r["src_port"]:<{c_sport}} '
                    f'{r["src_ip"]:<{c_sip}} {r["dest_ip"]:<{c_dip}}{extra}')
            print(boxline(line, width))

    print(hline('─', width, '└', '┘'))
    print()


def print_chain(chain_id, chain_info, rules, width):
    """Dispatch to compact or wide layout based on terminal width."""
    if width < 90:
        print_chain_compact(chain_id, chain_info, rules, width)
    else:
        print_chain_wide(chain_id, chain_info, rules, width)


def main():
    filepath = sys.argv[1] if len(sys.argv) > 1 else 'DM.txt'
    width = get_term_width()

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
    print(hline('═', width))
    print('  CHAIN SUMMARY')
    print(hline('═', width))
    # Adapt summary columns to width
    if width >= 70:
        c_id, c_name, c_alias, c_en, c_rules = 4, 26, 16, 4, 6
    else:
        c_id, c_name, c_alias, c_en, c_rules = 3, 18, 12, 3, 5
    print(f'  {"ID":<{c_id}} {"Name":<{c_name}} {"Alias":<{c_alias}} {"En":<{c_en}} {"Rules":<{c_rules}}')
    print(f'  {"─"*c_id} {"─"*c_name} {"─"*c_alias} {"─"*c_en} {"─"*c_rules}')
    for cid in sorted(chains.keys()):
        c = chains[cid]
        en = '🟢' if c['enable'] == '1' else '🔴'
        print(f'  {cid:<{c_id}} {c["name"]:<{c_name}} {c["alias"]:<{c_alias}} {en:<{c_en}} {c["rule_count"]:<{c_rules}}')
    print()


if __name__ == '__main__':
    main()
