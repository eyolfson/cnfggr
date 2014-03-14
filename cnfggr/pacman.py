import subprocess

class Database:

    IGNORED = {'bind': ['/etc/rndc.key'],
               'ca-certificates': ['/etc/ssl/certs/'],
               'dconf': ['/usr/lib/gio/modules/giomodule.cache',
                         '/usr/share/applications/mimeinfo.cache',
                         '/usr/share/icons/gnome/icon-theme.cache',
                         '/usr/share/icons/hicolor/icon-theme.cache'],
               'dhcpcd': ['/etc/dhcpcd.duid'],
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
               'nfs-utils': ['/etc/idmapd.conf'],
               'ntp': ['/etc/adjtime'],
               'openssh': ['/etc/ssh/'],
               'pango': ['/etc/pango/pango.modules'],
               'pacman': ['/etc/pacman.d/gnupg/'],
               'ppp': ['/etc/ppp/resolv.conf'],
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
