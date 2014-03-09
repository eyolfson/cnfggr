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
               'gummiboot': ['/boot/EFI/'],
               'libxml2': ['/etc/xml/'],
               'mkinitcpio': ['/boot/initramfs-linux.img',
                              '/boot/initramfs-linux-fallback.img'],
               'ntp': ['/etc/adjtime'],
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
        self.ignored_paths = set()
        for package, paths in Pacman.IGNORED.items():
            if not package in self.packages:
                continue
            for p in paths:
                self.ignored_paths.add(p)

    def is_package(self, p):
        return p in self.packages

    def is_disowned_path(self, p):
        return p not in self.owned_paths

    def is_ignored_path(self, p):
        return p in self.ignored_paths

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

    db = Pacman()

    config_files = set()
    for root, dirs, files in os.walk(config_dir, followlinks=False):
        if root != config_dir:
            for f in files:
                relpath = os.path.relpath(os.path.join(root, f), config_dir)
                package, f = relpath.split('/', maxsplit=1)
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
    disowned_dirs = []
    for root, dirs, files in os.walk('/', followlinks=False):
        if root == '/':
            skipped_dirs = [d for d in dirs if d not in root_dirs]
            for d in skipped_dirs:
                dirs.remove(d)

        skipped_dirs = []
        for d in dirs:
            # non-symlink directory paths end with /
            path = os.path.join(root, d)
            if not os.path.islink(path):
                path = '{}/'.format(path)

            disowned = db.is_disowned_path(path)
            ignored = db.is_ignored_path(path)
            if disowned or ignored:
                skipped_dirs.append(d)
            if disowned and not ignored:
                disowned_dirs.append(path)
        for d in skipped_dirs:
            dirs.remove(d)

        for f in files:
            path = os.path.join(root, f)
            disowned = db.is_disowned_path(path)
            ignored = db.is_ignored_path(path)
            config = path in config_files
            if disowned and (not ignored) and (not config):
                print_error('unmanaged file:', path)

    for d in disowned_dirs:
        for root, dirs, files in os.walk(d):
            for f in files:
                path = os.path.join(root, f)
                if not path in config_files:
                    print_error('unmanaged file:', path)
