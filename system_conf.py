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

import os
import subprocess
import sys

from collections import namedtuple

import ansi

class version(namedtuple('version', 'major minor patch extra')):

    def __str__(self):
        if self.extra == '':
            return 'v{}.{}.{}'.format( self.major
                                     , self.minor
                                     , self.patch
                                     )
        else:
            return 'v{}.{}.{}-{}'.format( self.major
                                        , self.minor
                                        , self.patch
                                        , self.extra
                                        )

version = version(0, 0, 0, 'development')

def print_version(file=sys.stdout):
    with ansi.sgr('34', file=file):
        print('system-conf', version, end='', file=file)
    print(file=file)

def pacman():
    return

def line_set(i):
    s = set()
    for l in i:
        s.add(l.rstrip(b'\n'))
    return s

def pacman_ignored(f):
    if not hasattr(pacman_ignored, 'files'):
        pacman_ignored.files =  {# filesystem
                                 b'/etc/group-',
                                 b'/etc/gshadow-',
                                 b'/etc/passwd-',
                                 b'/etc/shadow-',
                                 b'/etc/hostname',
                                 b'/etc/locale.conf',
                                 # glibc
                                 b'/etc/.pwd.lock',
                                 b'/etc/ld.so.cache',
                                 # mkinitcpio
                                 b'/boot/initramfs-linux.img',
                                 b'/boot/initramfs-linux-fallback.img',
                                 # systemd
                                 b'/etc/machine-id',
                                 # tzdata
                                 b'/etc/localtime'}
    if not hasattr(pacman_ignored, 'dirs'):
        pacman_ignored.dirs = [b'/etc/pacman.d/gnupg/',
                               b'/etc/ssl/certs/',
                               b'/etc/fonts/conf.d/',
                               b'/usr/share/mime/']
    if f in pacman_ignored.files:
        return True
    for d in pacman_ignored.dirs:
        if f.startswith(d):
            return True
    return False

def pacman_disowned():
    p = subprocess.Popen(['pacman', '-Qlq'], stdout=subprocess.PIPE)
    owned_files = line_set(p.stdout)
    p = subprocess.Popen(['sudo', 'find', '/boot', '/etc', '/opt', '/usr',
                          '!', '-name', 'lost+found', '(', '-type', 'd',
                          '-printf', '%p/\n', '-o', '-print', ')'],
                         stdout=subprocess.PIPE)
    all_files = line_set(p.stdout)
    for f in sorted(owned_files.difference(all_files)):
        if not os.path.lexists(f):
            with ansi.sgr('36'):
                print('[pacman-disowned]', end='')
            print(' ', end='')
            with ansi.sgr('31'):
                print(f.decode(), end='')
            print()
    for f in sorted(all_files.difference(owned_files)):
        if pacman_ignored(f):
            continue
        with ansi.sgr('36'):
            print('[pacman-disowned]', end='')
        print(' ', end='')
        with ansi.sgr('33'):
            print(f.decode(), end='')
        print()

def main():
    print_version()
    pacman_disowned()
