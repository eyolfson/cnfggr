#!/usr/bin/env python
#
# Copyright 2014 Jon Eyolfson
#
# This file is part of Cnfggr.
#
# Cnfggr is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# Cnfggr is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# Cnfggr. If not, see <http://www.gnu.org/licenses/>.

import os
import subprocess
import sys

from cnfggr import ansi
from cnfggr.version import get_version

print_title = ansi.print_func(ansi.BOLD, ansi.FG_BLUE)
print_success = ansi.print_func(ansi.FG_GREEN)
print_info = ansi.print_func(ansi.FG_BLUE)
print_warning = ansi.print_func(ansi.FG_YELLOW)
print_error = ansi.print_func(ansi.FG_RED)

def main():
    print_title('Cnfggr', get_version())
    if os.getuid() != 0:
        print_error('system mode requires root')
        exit(1)

    if len(sys.argv) != 2:
        config_dir = os.getcwd()
    else:
        config_dir = sys.argv[1]
    print_info('config directory:', config_dir)

    from cnfggr.pacman import Database
    db = Database()
    PACKAGE_DEPTH = 1

    config_files = set()
    for root, dirs, files in os.walk(config_dir, followlinks=False):
        if root != config_dir:
            for f in files:
                relpath = os.path.relpath(os.path.join(root, f), config_dir)
                split = relpath.split('/', maxsplit=PACKAGE_DEPTH)
                package = '/'.join(split[:-1])
                f = split[-1]
                path = os.path.join('/', f)
                config_files.add(path)
                command = ['diff', '-q', '--no-dereference', relpath, path]
                subprocess.call(command)
        else:
            skipped_dirs = []
            for d in dirs:
                if d.startswith('.'):
                    skipped_dirs.append(d)
                elif not db.is_package(d):
                    print_error('missing package:', d)
                    skipped_dirs.append(d)
            for d in skipped_dirs:
                dirs.remove(d)

    root_dirs = {'boot', 'etc', 'opt', 'usr'}
    unmanaged_dirs = []
    for root, dirs, files in os.walk('/', followlinks=False):
        if root == '/':
            skipped_dirs = [d for d in dirs if d not in root_dirs]
            for d in skipped_dirs:
                dirs.remove(d)

        skipped_dirs = []
        for d in dirs:
            # symlinks are included in dirs bit their path appears as a file
            # directory paths always end with /
            path = os.path.join(root, d)
            if not os.path.islink(path):
                path = '{}/'.format(path)

            disowned = db.is_disowned_path(path)
            ignored = db.is_ignored_path(path)
            if disowned or ignored:
                skipped_dirs.append(d)
            if disowned and not ignored:
                unmanaged_dirs.append(path)
        for d in skipped_dirs:
            dirs.remove(d)

        for f in files:
            path = os.path.join(root, f)
            disowned = db.is_disowned_path(path)
            ignored = db.is_ignored_path(path)
            config = path in config_files
            if disowned and (not ignored) and (not config):
                print_error('unmanaged file:', path)

    # A non-configuration file in an unmanaged directory is unmanaged itself
    for d in unmanaged_dirs:
        empty = True
        for root, dirs, files in os.walk(d):
            for f in files:
                path = os.path.join(root, f)
                if not path in config_files:
                    print_error('unmanaged file:', path)
            if empty and len(files) > 0:
                empty = False
        if empty:
            print_warning('unmanaged empty directory:', d)
