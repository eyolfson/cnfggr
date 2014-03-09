# Copyright 2014 Jon Eyolfson
# Copyright 2014 Jean-Christophe Petkovich
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

import subprocess
import os

class Database:

    IGNORED = {'sys-apps/portage': ['/usr/portage/']}

    def __init__(self):
        self.packages = set()
        with subprocess.Popen(['eix', '-I', '--only-names'],
                              env={'EIX_LIMIT': '0'},
                              stdout=subprocess.PIPE,
                              universal_newlines=True) as p:
            for l in p.stdout:
                self.packages.add(l.rstrip('\n'))
        self.owned_paths = set()
        for p in self.packages:
            with subprocess.Popen(['equery', 'files', p],
                                  stdout=subprocess.PIPE,
                                  universal_newlines=True) as p:
                for l in p.stdout:
                    path = l.rstrip('\n')
                    if os.path.isdir(path) and not os.path.islink(path):
                        path = '{}/'.format(path)
                    self.owned_paths.add(path)
        self.ignored_paths = set()
        for package, paths in Database.IGNORED.items():
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
