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
from subprocess import Popen, PIPE, call
from sys import stdin, stdout

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

class command:

    def __init__(self, args, **kwargs):
        self.args = args
        self.display_args = [x.decode() if isinstance(x, bytes) else x
                             for x in args]
        self.kwargs = kwargs

    def __enter__(self):
        if self.args[0] == 'sudo':
            with prefixer(command.__name__):
                with ansi.sgr('34'):
                    stdout.write(' '.join(self.display_args))
        self.process = Popen(self.args, **self.kwargs)
        return self.process

    def __exit__(self, type, value, trackpack):
        self.process.wait()

def command_stdout_to_set(args):
    s = set()
    with command(args, stdout=PIPE) as p:
        for l in p.stdout:
            s.add(l.rstrip(b'\n'))
    return s

ignored_files = [ ( 'dconf', [ b'/usr/lib/gio/modules/giomodule.cache',
                               b'/usr/share/applications/mimeinfo.cache',
                               b'/usr/share/icons/gnome/icon-theme.cache',
                               b'/usr/share/icons/hicolor/icon-theme.cache' ] ),
                  ( 'dhcpcd', [ b'/etc/dhcpcd.duid' ] ),
                  ( 'filesystem', [ b'/etc/group-',
                                    b'/etc/gshadow-',
                                    b'/etc/passwd-',
                                    b'/etc/shadow-' ] ),
                  ( 'gconf', [ b'/usr/lib/gio/modules/giomodule.cache' ] ),
                  ( 'glibc', [ b'/etc/.pwd.lock',
                               b'/etc/ld.so.cache',
                               b'/usr/lib/locale/locale-archive' ] ),
                  ( 'mkinitcpio', [ b'/boot/initramfs-linux.img',
                                    b'/boot/initramfs-linux-fallback.img' ] ),
                  ( 'pango', [ b'/etc/pango/pango.modules' ] ),
                  ( 'systemd', [ b'/etc/machine-id',
                                 b'/etc/udev/hwdb.bin' ] ),
                  ( 'texinfo', [ b'/usr/share/info/dir' ] ) ]

class pacman:

    def __init__(self):
        self.file = stdout
        self.installed_packages = command_stdout_to_set([ 'pacman', '-Qq' ])
        self.ignored_files = { # gdk-pixbuf2
                               b'/usr/lib/gdk-pixbuf-2.0/2.10.0/loaders.cache',
                               # glib2
                               b'/usr/share/glib-2.0/schemas/gschemas.compiled',
                               # gtk2 (based off immodules)
                               b'/usr/lib/gtk-2.0/2.10.0/immodules.cache',
                               # gtk3 (based off immodules)
                               b'/usr/lib/gtk-3.0/3.0.0/immodules.cache',
                               # xorg-mkfontdir
                               b'/usr/share/fonts/TTF/fonts.dir',
                               b'/usr/share/fonts/misc/fonts.dir',
                               # xorg-mkfontscale
                               b'/usr/share/fonts/TTF/fonts.scale',
                               b'/usr/share/fonts/misc/fonts.scale' }
        for package, files in ignored_files:
            if self.installed(package, warn=False):
                for f in files:
                    self.ignored_files.add(f)
        self.ignored_dirs = [ # ca-certificates
                              b'/etc/ssl/certs/',
                              # fontconfig
                              b'/etc/fonts/conf.d/',
                              # pacman
                              b'/etc/pacman.d/gnupg/',
                              # shared-mime-info
                              b'/usr/share/mime/' ]

    def ignored(self, f):
        if f in self.ignored_files:
            return True
        for d in self.ignored_dirs:
            if f.startswith(d):
                return True
        return False

    def add_ignored_file(self, f):
        self.ignored_files.add(f)
        i = len(f)
        while True:
            i = f.rfind(b'/', 0, i)
            if i == 0: break
            self.ignored_files.add(f[:i+1])

    def disowned(self):
        prefix = prefixer(self.disowned.__name__)
        owned_files = command_stdout_to_set([ 'pacman', '-Qlq' ])
        all_command = [ 'sudo', 'find', '/boot', '/etc', '/opt', '/usr', '!',
                        '-name', 'lost+found', '(', '-type', 'd', '-printf',
                        r'%p/\n', '-o', '-print', ')' ]
        all_files = command_stdout_to_set(all_command)
        ignore_options = False
        for f in sorted(owned_files.difference(all_files)):
            if not path.lexists(f):
                with prefix:
                    with ansi.sgr('31'):
                        self.file.write(f.decode())
                    self.file.write(' does not exist')
        for f in sorted(all_files.difference(owned_files), reverse=True):
            if self.ignored(f):
                continue
            with prefix:
                with ansi.sgr('33'):
                    self.file.write(f.decode())
                self.file.write(' not owned')

            if not ignore_options:
                with prefix:
                    stdout.write('Options: i - ignore, a - ignore all, r - remove')
                option = stdin.readline().rstrip('\n')

                if option == 'a':
                    ignore_options = True
                elif option == 'r':
                    if f.endswith(b'/'):
                        with command(['sudo', 'rmdir', f]): pass
                    else:
                        with command(['sudo', 'rm', f]): pass

    def installed(self, package, warn=True):
        if fsencode(package) in self.installed_packages:
            return True
        else:
            if warn:
                with prefixer(self.installed.__name__):
                    with ansi.sgr('33'):
                        self.file.write(package)
                    self.file.write(' not installed')
            return False

def update(src_filename, dest_filename):
    prefix = prefixer(update.__name__)
    if not path.lexists(dest_filename):
        with prefix:
            with ansi.sgr('33'):
                stdout.write(dest_filename.decode())
            stdout.write(' copying')
        dest_dirname = path.dirname(dest_filename)
        with command(['sudo', 'mkdir', '-p', dest_dirname]): pass
        with command(['sudo', 'cp', '-P', src_filename, dest_filename]): pass
        return

    with command(['sudo', 'diff', '-u', '--no-dereference',
                  src_filename, dest_filename], stdout=PIPE) as p:
        p.wait()
        if p.returncode == 0:
            return
        diff = p.stdout

    with prefix:
        with ansi.sgr('33'):
            stdout.write(dest_filename.decode())
        stdout.write(' differs')

    with prefix:
        stdout.write('Options: i - ignore, d - show diff, o - ours, t - theirs')
    option = stdin.readline().rstrip('\n')

    if option == 'd':
        for line in diff:
            display_line = line.rstrip(b'\n').decode()
            with prefixer('diff'):
                if display_line.startswith('+'):
                    with ansi.sgr('32'):
                        stdout.write(display_line)
                elif display_line.startswith('-'):
                    with ansi.sgr('31'):
                        stdout.write(display_line)
                else:
                    stdout.write(display_line)
        with prefix:
            stdout.write('Options: i - ignore, o - ours, t - theirs')
        option = stdin.readline().rstrip('\n')

    if option == 'o':
        with command(['sudo', 'cp', '-P', src_filename, dest_filename]): pass
    elif option == 't':
        with command(['cp', '-P', dest_filename, src_filename]): pass

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
                src_filename = path.join(root, f)
                rel_path = path.relpath(src_filename, current_dir)
                dest_filename = fsencode(path.join('/', rel_path))
                update(src_filename, dest_filename)
                db.add_ignored_file(dest_filename)
    db.disowned()
