#!/usr/bin/env python3
"""
Controller for TR-181 visualizer scripts in dm_visualizers/.

Usage:
  python3 visualize.py [visualizer] [DM.txt]
  python3 visualize.py [DM.txt]
"""

import glob
import os
import subprocess
import sys

try:
    import readline
except ImportError:
    readline = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VIS_DIR = os.path.join(BASE_DIR, 'dm_visualizers')


def discover_visualizers():
    if not os.path.isdir(VIS_DIR):
        return []
    entries = []
    for name in os.listdir(VIS_DIR):
        if not name.endswith('.py'):
            continue
        if name.startswith('_'):
            continue
        if not name.startswith('show_'):
            continue
        path = os.path.join(VIS_DIR, name)
        if os.path.isfile(path):
            entries.append({
                'file': name,
                'name': os.path.splitext(name)[0],
                'path': path,
            })
    return sorted(entries, key=lambda item: item['name'])


def resolve_visualizer(arg, entries):
    if not arg:
        return None
    for entry in entries:
        if arg == entry['name'] or arg == entry['file']:
            return entry
    lowered = arg.lower()
    matches = [
        entry for entry in entries
        if entry['name'].lower().startswith(lowered)
        or entry['file'].lower().startswith(lowered)
    ]
    if len(matches) == 1:
        return matches[0]
    return None


def print_list(entries):
    for idx, entry in enumerate(entries, 1):
        print(f'  {idx}. {entry["name"]} ({entry["file"]})')


def select_interactive(entries):
    print('Available visualizers:')
    print_list(entries)
    while True:
        choice = input(f'Select visualizer [1-{len(entries)} or name]: ').strip()
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(entries):
                return entries[idx - 1]
        if choice:
            resolved = resolve_visualizer(choice, entries)
            if resolved:
                return resolved
            matches = [
                entry for entry in entries
                if entry['name'].lower().startswith(choice.lower())
                or entry['file'].lower().startswith(choice.lower())
            ]
            if matches:
                print('Matches:')
                print_list(matches)
                continue
        print('Invalid selection. Try again.')


def usage(entries):
    print('Usage: python3 visualize.py [visualizer] [DM.txt]')
    print('       python3 visualize.py [DM.txt]')
    print()
    print('Available visualizers:')
    print_list(entries)


def _completion_fragment(text):
    if not readline:
        return text
    try:
        buffer = readline.get_line_buffer()
        beg = readline.get_begidx()
        end = readline.get_endidx()
        fragment = buffer[beg:end]
        return fragment if fragment else text
    except Exception:
        return text


def path_completer(text, state):
    fragment = _completion_fragment(text)
    expanded = os.path.expanduser(fragment)
    dir_part = os.path.dirname(expanded)
    base = os.path.basename(expanded)
    if not dir_part:
        dir_part = '.'
    pattern = os.path.join(dir_part, base + '*')
    matches = glob.glob(pattern)
    matches = [m + '/' if os.path.isdir(m) else m for m in matches]
    matches = sorted(set(matches))
    if not matches:
        return None

    orig_dir = os.path.dirname(fragment)
    if orig_dir:
        orig_dir = orig_dir.rstrip(os.path.sep) + os.path.sep
    else:
        orig_dir = ''

    try:
        candidate = matches[state]
    except IndexError:
        return None

    name = os.path.basename(candidate.rstrip(os.path.sep))
    suffix = os.path.sep if candidate.endswith(os.path.sep) else ''
    return f'{orig_dir}{name}{suffix}'


def set_readline_completer(completer):
    if not readline:
        return None
    previous = readline.get_completer()
    try:
        previous_delims = readline.get_completer_delims()
    except AttributeError:
        previous_delims = None
    readline.set_completer(completer)
    readline.parse_and_bind('tab: complete')
    if previous_delims is not None:
        readline.set_completer_delims(' \t\n')
    return (previous, previous_delims)


def restore_readline(previous):
    if not readline or previous is None:
        return
    prev_completer, prev_delims = previous
    readline.set_completer(prev_completer)
    if prev_delims is not None:
        readline.set_completer_delims(prev_delims)


def prompt_dm_path(default_path=None):
    previous = set_readline_completer(path_completer)
    while True:
        if default_path:
            prompt = f'DM file [{default_path}]: '
        else:
            prompt = 'DM file path: '
        value = input(prompt).strip()
        if not value and default_path:
            restore_readline(previous)
            return default_path
        if value and os.path.isfile(value):
            restore_readline(previous)
            return value
        print('File not found. Try again.')


def main():
    entries = discover_visualizers()
    if not entries:
        print(f'No visualizers found in {VIS_DIR}')
        sys.exit(1)

    print(f'Found {len(entries)} visualizer(s) in dm_visualizers/')

    args = sys.argv[1:]
    dm_path = None
    selected = None

    if args:
        selected = resolve_visualizer(args[0], entries)
        if selected:
            if len(args) > 1:
                dm_path = args[1]
        else:
            if len(args) == 1 and (args[0].endswith('.txt') or os.path.exists(args[0])):
                dm_path = args[0]
            else:
                usage(entries)
                sys.exit(2)

    if not selected:
        selected = select_interactive(entries)

    if not dm_path:
        default_dm = os.path.join(BASE_DIR, 'DM.txt')
        if os.path.isfile(default_dm):
            dm_path = prompt_dm_path(default_dm)
        else:
            dm_path = prompt_dm_path()

    cmd = [sys.executable, selected['path']]
    if dm_path:
        cmd.append(dm_path)
    print(f'Running {selected["file"]} ...')
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


if __name__ == '__main__':
    main()
