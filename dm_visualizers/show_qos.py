#!/usr/bin/env python3
"""
Parse DM.txt and display TR-181 Device.QoS classifications, queues, and shapers
as a text-based visualized diagram.

Usage: python3 dm_visualizers/show_qos.py [DM.txt]

References:
  - Broadband Forum TR-181 Device:2 Data Model (Device.QoS)
  - prpl Foundation tr181-qos plugin
    https://gitlab.com/prpl-foundation/components/core/plugins/tr181-qos
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


def proto_label(value):
    mapping = {'-1': 'any', '1': 'ICMP', '6': 'TCP', '17': 'UDP', '58': 'ICMPv6'}
    return mapping.get(str(value), str(value))


def filter_label(ip, mask):
    ip = nonempty(ip, '')
    mask = nonempty(mask, '')
    if not ip:
        return '*'
    return f'{ip}/{mask}' if mask else ip


def discover_classifications(dm):
    pat = re.compile(r'^Device\.QoS\.Classification\.(\d+)\.(Alias|Status)$')
    ids = set()
    for key in dm:
        m = pat.match(key)
        if m:
            ids.add(int(m.group(1)))
    rows = []
    for cid in sorted(ids):
        prefix = f'Device.QoS.Classification.{cid}'
        rows.append({
            'id': cid,
            'alias': nonempty(get_attr(dm, prefix, 'Alias')),
            'enable': get_attr(dm, prefix, 'Enable') or '0',
            'status': nonempty(get_attr(dm, prefix, 'Status')),
            'order': nonempty(get_attr(dm, prefix, 'Order')),
            'ip_version': nonempty(get_attr(dm, prefix, 'IPVersion')),
            'protocol': proto_label(get_attr(dm, prefix, 'Protocol') or '-1'),
            'interface': nonempty(normalize_ref(get_attr(dm, prefix, 'Interface'))),
            'source': filter_label(get_attr(dm, prefix, 'SourceIP'), get_attr(dm, prefix, 'SourceMask')),
            'dest': filter_label(get_attr(dm, prefix, 'DestIP'), get_attr(dm, prefix, 'DestMask')),
            'traffic_class': nonempty(get_attr(dm, prefix, 'TrafficClass')),
            'direction': nonempty(get_attr(dm, prefix, 'X_PRPLWARE-COM_Direction')),
        })
    return rows


def discover_queues(dm):
    pat = re.compile(r'^Device\.QoS\.Queue\.(\d+)\.(Alias|Status)$')
    ids = set()
    for key in dm:
        m = pat.match(key)
        if m:
            ids.add(int(m.group(1)))
    rows = []
    for qid in sorted(ids):
        prefix = f'Device.QoS.Queue.{qid}'
        rows.append({
            'id': qid,
            'alias': nonempty(get_attr(dm, prefix, 'Alias')),
            'enable': get_attr(dm, prefix, 'Enable') or '0',
            'status': nonempty(get_attr(dm, prefix, 'Status')),
            'interface': nonempty(normalize_ref(get_attr(dm, prefix, 'Interface'))),
            'precedence': nonempty(get_attr(dm, prefix, 'Precedence')),
            'scheduler': nonempty(get_attr(dm, prefix, 'SchedulerAlgorithm')),
            'rate': nonempty(get_attr(dm, prefix, 'ShapingRate')),
            'classes': nonempty(get_attr(dm, prefix, 'TrafficClasses')),
            'weight': nonempty(get_attr(dm, prefix, 'Weight')),
        })
    return rows


def discover_shapers(dm):
    pat = re.compile(r'^Device\.QoS\.Shaper\.(\d+)\.(Alias|Status)$')
    ids = set()
    for key in dm:
        m = pat.match(key)
        if m:
            ids.add(int(m.group(1)))
    rows = []
    for sid in sorted(ids):
        prefix = f'Device.QoS.Shaper.{sid}'
        rows.append({
            'id': sid,
            'alias': nonempty(get_attr(dm, prefix, 'Alias')),
            'enable': get_attr(dm, prefix, 'Enable') or '0',
            'status': nonempty(get_attr(dm, prefix, 'Status')),
            'interface': nonempty(normalize_ref(get_attr(dm, prefix, 'Interface'))),
            'rate': nonempty(get_attr(dm, prefix, 'ShapingRate')),
            'burst': nonempty(get_attr(dm, prefix, 'ShapingBurstSize')),
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


def print_overview(dm, classifications, queues, shapers, width):
    lines = [
        f'Classifications: {len(classifications)} / {nonempty(get_attr(dm, "Device.QoS", "ClassificationNumberOfEntries"))}',
        f'Queues: {len(queues)} / {nonempty(get_attr(dm, "Device.QoS", "QueueNumberOfEntries"))}',
        f'Shapers: {len(shapers)} / {nonempty(get_attr(dm, "Device.QoS", "ShaperNumberOfEntries"))}',
    ]
    box_w = box_width(width, lines, title='TR-181 QOS OVERVIEW')
    print(hline('═', box_w, '╔', '╗'))
    print(f'║{"TR-181 QOS OVERVIEW":^{box_w - 2}}║')
    print(hline('═', box_w, '╠', '╣'))
    for line in lines:
        print(boxline(line, box_w))
    print(hline('═', box_w, '╚', '╝'))
    print()


def matched_queue_aliases(classifications, queues):
    matched = {}
    queue_by_class = {}
    for queue in queues:
        classes = {part.strip() for part in queue['classes'].split(',') if part.strip() and part.strip() != '-'}
        for cls in classes:
            queue_by_class.setdefault(cls, []).append(queue['alias'])
    for cls in classifications:
        matched[cls['id']] = ', '.join(queue_by_class.get(cls['traffic_class'], [])) or '-'
    return matched


def print_compact(classifications, queues, shapers, width):
    matched = matched_queue_aliases(classifications, queues)
    class_lines = []
    for row in classifications:
        class_lines.append(
            f'#{row["order"]} {row["alias"]}  {format_enable(row["enable"])} {row["status"]}  '
            f'v{row["ip_version"]} {row["protocol"]} class={row["traffic_class"]} dir={row["direction"]}'
        )
        class_lines.append(f'  src={row["source"]} dst={row["dest"]} if={row["interface"]} queue={matched[row["id"]]}')
    print_line_box('Classifications', class_lines, width)

    queue_lines = []
    for row in queues:
        queue_lines.append(
            f'#{row["id"]} {row["alias"]}  {format_enable(row["enable"])} {row["status"]}  '
            f'if={row["interface"]} prec={row["precedence"]} sched={row["scheduler"]}'
        )
        queue_lines.append(f'  classes={row["classes"]} rate={row["rate"]} weight={row["weight"]}')
    print_line_box('Queues', queue_lines, width)

    shaper_lines = [
        f'#{row["id"]} {row["alias"]}  {format_enable(row["enable"])} {row["status"]}  '
        f'if={row["interface"]} rate={row["rate"]} burst={row["burst"]}'
        for row in shapers
    ]
    print_line_box('Shapers', shaper_lines, width)


def print_wide(classifications, queues, shapers, width):
    matched = matched_queue_aliases(classifications, queues)
    class_rows = []
    for row in classifications:
        class_rows.append({
            'order': row['order'],
            'alias': row['alias'],
            'en': format_enable(row['enable']),
            'status': row['status'],
            'proto': f'v{row["ip_version"]}/{row["protocol"]}',
            'source': row['source'],
            'dest': row['dest'],
            'class': row['traffic_class'],
            'queue': matched[row['id']],
        })
    print_subtable(
        'Classifications',
        [
            ('order', 'Ord', 3),
            ('alias', 'Alias', 16),
            ('en', 'En', 2),
            ('status', 'Status', 8),
            ('proto', 'Proto', 8),
            ('source', 'Source', 12),
            ('dest', 'Dest', 12),
            ('class', 'Class', 5),
            ('queue', 'Queue', 10),
        ],
        class_rows,
        width,
    )

    queue_rows = []
    for row in queues:
        queue_rows.append({
            'id': str(row['id']),
            'alias': row['alias'],
            'en': format_enable(row['enable']),
            'status': row['status'],
            'iface': row['interface'],
            'prec': row['precedence'],
            'sched': row['scheduler'],
            'class': row['classes'],
            'rate': row['rate'],
        })
    print_subtable(
        'Queues',
        [
            ('id', '#', 2),
            ('alias', 'Alias', 14),
            ('en', 'En', 2),
            ('status', 'Status', 8),
            ('iface', 'Interface', 16),
            ('prec', 'Prec', 4),
            ('sched', 'Sched', 5),
            ('class', 'TrafficClasses', 10),
            ('rate', 'Rate', 6),
        ],
        queue_rows,
        width,
    )

    shaper_rows = []
    for row in shapers:
        shaper_rows.append({
            'id': str(row['id']),
            'alias': row['alias'],
            'en': format_enable(row['enable']),
            'status': row['status'],
            'iface': row['interface'],
            'rate': row['rate'],
            'burst': row['burst'],
        })
    print_subtable(
        'Shapers',
        [
            ('id', '#', 2),
            ('alias', 'Alias', 14),
            ('en', 'En', 2),
            ('status', 'Status', 8),
            ('iface', 'Interface', 16),
            ('rate', 'Rate', 6),
            ('burst', 'Burst', 5),
        ],
        shaper_rows,
        width,
    )


def print_summary(queues, width):
    rows = []
    iface_w = 16 if width < WIDE_THRESHOLD else 20
    alias_w = 14 if width < WIDE_THRESHOLD else 18
    for row in queues:
        rows.append({
            'id': str(row['id']),
            'alias': fit_display(row['alias'], alias_w),
            'iface': fit_display(row['interface'], iface_w),
            'prec': row['precedence'],
            'class': row['classes'],
            'status': row['status'],
        })
    lines = ['  QOS QUEUE SUMMARY']
    lines.extend(render_table(
        [
            ('id', 'ID', 2),
            ('alias', 'Queue', alias_w),
            ('iface', 'Interface', iface_w),
            ('prec', 'Prec', 4),
            ('class', 'Class', 5),
            ('status', 'Status', 8),
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
    classifications = discover_classifications(dm)
    queues = discover_queues(dm)
    shapers = discover_shapers(dm)
    print_overview(dm, classifications, queues, shapers, width)
    if width < WIDE_THRESHOLD:
        print_compact(classifications, queues, shapers, width)
    else:
        print_wide(classifications, queues, shapers, width)
    print_summary(queues, width)


if __name__ == '__main__':
    main()
