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
        with subprocess.Popen(['equery', 'files'], stdout=subprocess.PIPE,
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
