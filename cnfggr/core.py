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

from os import fsencode, path, walk
from subprocess import Popen, PIPE, call
from sys import stdin, stdout

print_title = ansi.print_func(ansi.BOLD, ansi.FG_BLUE)
print_success = ansi.print_func(ansi.FG_GREEN)
print_info = ansi.print_func(ansi.FG_BLUE)
print_warning = ansi.print_func(ansi.FG_YELLOW)
print_error = ansi.print_func(ansi.FG_RED)

PRINT_DISOWNED = True

class Pacman:

    IGNORED = {'ca-certificates': ['/etc/ssl/certs/'],
               'dconf': ['/usr/lib/gio/modules/giomodule.cache',
                         '/usr/share/applications/mimeinfo.cache',
                         '/usr/share/icons/gnome/icon-theme.cache',
                         '/usr/share/icons/hicolor/icon-theme.cache'],
               'dhcpcd': ['/etc/dhcpcd.duid'],
               'fontconfig': ['/etc/fonts/conf.d/'],
               'filesystem': ['/etc/group-',
                              '/etc/gshadow-',
                              '/etc/passwd-',
                              '/etc/shadow-'],
               'gconf': ['/usr/lib/gio/modules/giomodule.cache'],
               'gdk-pixbuf2': ['/usr/lib/gdk-pixbuf-2.0/2.10.0/loaders.cache'],
               'glib2': ['/usr/share/glib-2.0/schemas/gschemas.compiled'],
               'glibc': ['/etc/.pwd.lock',
                         '/etc/ld.so.cache',
                         '/usr/lib/locale/locale-archive'] ,
               'gtk2': ['/usr/lib/gtk-2.0/2.10.0/immodules.cache'],
               'gtk3': ['/usr/lib/gtk-3.0/3.0.0/immodules.cache'],
               'libxml2': ['/etc/xml/'],
               'mkinitcpio': ['/boot/initramfs-linux.img',
                              '/boot/initramfs-linux-fallback.img'],
               'openssh': ['/etc/ssh/'],
               'pango': ['/etc/pango/pango.modules'],
               'pacman': ['/etc/pacman.d/gnupg/'],
               'shared-mime-info': ['/usr/share/mime/'],
               'systemd': ['/etc/machine-id',
                           '/etc/udev/hwdb.bin'],
               'texinfo': ['/usr/share/info/dir'],
               'texlive-bin': ['/usr/share/texmf-dist/ls-R',
                               '/etc/texmf/ls-R'],
               'xorg-mkfontdir': ['/usr/share/fonts/TTF/fonts.dir',
                                  '/usr/share/fonts/Type1/fonts.dir',
                                  '/usr/share/fonts/misc/fonts.dir'],
               'xorg-mkfontscale': ['/usr/share/fonts/TTF/fonts.scale',
                                    '/usr/share/fonts/Type1/fonts.scale',
                                    '/usr/share/fonts/misc/fonts.scale']}

    def __init__(self):
        self.packages = set()
        with subprocess.Popen(['pacman', '-Qq'], stdout=subprocess.PIPE,
                              universal_newlines=True) as p:
            for l in p.stdout:
                self.packages.add(l.rstrip('\n'))
        self.owned_paths = set()
        with subprocess.Popen(['pacman', '-Qlq'], stdout=subprocess.PIPE,
                              universal_newlines=True) as p:
            for l in p.stdout:
                self.owned_paths.add(l.rstrip('\n'))
        self.ignored_dirs = []
        self.ignored_files = set()
        for package, paths in Pacman.IGNORED.items():
            if not package in self.packages:
                continue
            for p in paths:
                if p.endswith('/'):
                    self.ignored_dirs.append(p)
                else:
                    self.ignored_files.add(p)

    def is_package(self, p):
        return p in self.packages

    def is_path(self, p):
        if p in self.owned_paths:
            return True
        if p in self.ignored_files:
            return True
        for ignored_dir in self.ignored_dirs:
            if p.startswith(ignored_dir):
                return True
        return False

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
    config_files = {}
    for root, dirs, files in os.walk(config_dir):
        dirs = [d for d in dirs if not d.startswith('.')]
        if root != config_dir:
            for f in files:
                relpath = os.path.relpath(os.path.join(root, f), config_dir)
                package, path = relpath.split('/', maxsplit=1)
                if package in config_files:
                    config_files[package].append(path)
                else:
                    config_files[package] = [path]

    db = Pacman()
    for package, files in config_files.items():
        if not db.is_package(package):
            print_error('missing package:', package)
            continue
        for f in files:
            path = os.path.join('/', f)
            config_path = os.path.join(config_dir, package, f)
            subprocess.call(['diff', '-q', '--no-dereference', path,
                             config_path])

    if not PRINT_DISOWNED:
        return

    root_dirs = {'boot', 'etc', 'opt', 'usr'}
    for root, dirs, files in os.walk('/'):
        if root == '/':
            ignored_dirs = [d for d in dirs if d not in root_dirs]
            for d in ignored_dirs:
                dirs.remove(d)

        disowned_dirs = []
        for d in dirs:
            path = os.path.join(root, d)
            # non-symlink directory paths end with /
            if not os.path.islink(path):
                path = '{}/'.format(path)
            if not db.is_path(path):
                disowned_dirs.append(d)
                print_error('disowned directory:', path)
        for d in disowned_dirs:
            dirs.remove(d)

        for f in files:
            path = os.path.join(root, f)
            if not db.is_path(path):
                print_error('disowned file:', path) 
