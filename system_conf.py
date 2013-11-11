# Copyright 2013 Jon Eyolfson
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from collections import namedtuple
from os import fsencode, path, walk
from sys import stdout

import ansi

class version(namedtuple('version', 'major minor patch extra')):

    def __str__(self):
        if self.extra == '':
            return 'v{}.{}.{}'.format(self.major, self.minor, self.patch)
        else:
            return 'v{}.{}.{}-{}'.format(self.major, self.minor, self.patch,
                                         self.extra)

    def display(self, file=stdout):
        with ansi.sgr('34', file=file):
            file.write('system-conf ')
            file.write(str(version))
        file.write('\n')

version = version(0, 0, 0, 'development')

class prefixer:

    def __init__(self, prefix, file=stdout):
        self.prefix = prefix
        self.file = file

    def __enter__(self):
        with ansi.sgr('36'):
            self.file.write('[')
            self.file.write(self.prefix)
            self.file.write(']')
        self.file.write(' ')

    def __exit__(self, type, value, traceback):
        self.file.write('\n')

class pacman:

    def __init__(self):
        self.file = stdout
        self.installed_packages = self._command_to_set([ 'pacman', '-Qq' ])
        self.ignored_files = { # dconf
                               b'/usr/lib/gio/modules/giomodule.cache',
                               b'/usr/share/applications/mimeinfo.cache',
                               b'/usr/share/icons/hicolor/icon-theme.cache',
                               # dhcpcd
                               b'/etc/dhcpcd.duid',
                               # filesystem
                               b'/etc/group-',
                               b'/etc/gshadow-',
                               b'/etc/passwd-',
                               b'/etc/shadow-',
                               # gconf
                               b'/usr/lib/gio/modules/giomodule.cache',
                               # gdk-pixbuf2
                               b'/usr/lib/gdk-pixbuf-2.0/2.10.0/loaders.cache',
                               # glib2
                               b'/usr/share/glib-2.0/schemas/gschemas.compiled',
                               # glibc
                               b'/etc/.pwd.lock',
                               b'/etc/ld.so.cache',
                               b'/usr/lib/locale/locale-archive',
                               # gtk2 (based off immodules)
                               b'/usr/lib/gtk-2.0/2.10.0/immodules.cache',
                               # gtk3 (based off immodules)
                               b'/usr/lib/gtk-3.0/3.0.0/immodules.cache',
                               # mkinitcpio
                               b'/boot/initramfs-linux.img',
                               b'/boot/initramfs-linux-fallback.img',
                               # pango
                               b'/etc/pango/pango.modules',
                               # systemd
                               b'/etc/machine-id',
                               b'/etc/udev/hwdb.bin',
                               # texinfo
                               b'/usr/share/info/dir',
                               # xorg-mkfontdir
                               b'/usr/share/fonts/TTF/fonts.dir',
                               b'/usr/share/fonts/misc/fonts.dir',
                               # xorg-mkfontscale
                               b'/usr/share/fonts/TTF/fonts.scale',
                               b'/usr/share/fonts/misc/fonts.scale' }
        self.ignored_dirs = [ # ca-certificates
                              b'/etc/ssl/certs/',
                              # fontconfig
                              b'/etc/fonts/conf.d/',
                              # pacman
                              b'/etc/pacman.d/gnupg/',
                              # shared-mime-info
                              b'/usr/share/mime/',
                              # systemd
                              b'/etc/systemd/system/getty.target.wants/',
                              b'/etc/systemd/system/multi-user.target.wants/' ]

    def _command_to_set(self, command):
        with prefixer('command'):
            with ansi.sgr('32'):
                self.file.write(' '.join(command))
        from subprocess import Popen, PIPE
        p = Popen(command, stdout=PIPE)
        s = set()
        for l in p.stdout:
            s.add(l.rstrip(b'\n'))
        p.wait()
        return s

    def _ignored(self, f):
        if f in self.ignored_files:
            return True
        for d in self.ignored_dirs:
            if f.startswith(d):
                return True
        return False

    def add_ignored_file(self, f):
        self.ignored_files.add(f)

    def disowned(self):
        p = prefixer(self.disowned.__name__)
        owned_command = [ 'pacman', '-Qlq' ]
        all_command = [ 'sudo', 'find', '/boot', '/etc', '/opt', '/usr', '!',
                        '-name', 'lost+found', '(', '-type', 'd', '-printf',
                        '%p/\n', '-o', '-print', ')' ]
        owned_files = self._command_to_set(owned_command)
        all_files = self._command_to_set(all_command)
        for f in sorted(owned_files.difference(all_files)):
            if not path.lexists(f):
                with p:
                    with ansi.sgr('31'):
                        self.file.write(f.decode())
                    self.file.write(' does not exist')
        for f in sorted(all_files.difference(owned_files)):
            if self._ignored(f):
                continue
            with p:
                with ansi.sgr('33'):
                    self.file.write(f.decode())
                self.file.write(' not owned')

    def installed(self, p):
        if fsencode(p) in self.installed_packages:
            return True
        else:
            with prefixer(self.installed.__name__):
                with ansi.sgr('33'):
                    self.file.write(p)
                self.file.write(' not installed')
            return False

def main():
    version.display()
    git_dir = path.dirname(path.abspath(__file__))
    db = pacman()
    for root, dirs, filenames in walk(git_dir):
        if root == git_dir:
            package_dirs = []
            for d in dirs:
                if d == '.git' or d == '__pycache__':
                    continue
                if db.installed(d):
                    package_dirs.append(d)
            dirs[:] = package_dirs
        elif path.dirname(root) == git_dir:
            current_dir = root
        else:
            for f in filenames:
                rel_path = path.relpath(path.join(root, f), current_dir)
                dest_file = fsencode(path.join('/', rel_path))
                p.add_ignored_file(dest_file)
    db.disowned()
