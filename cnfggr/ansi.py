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

import sys

class SGR:
    RESET = '0'
    BOLD = '1'
    FG_RED = '31'
    FG_GREEN = '32'
    FG_YELLOW = '33'
    FG_BLUE = '34'
    FG_MAGENTA = '35'
    FG_CYAN = '36'

class sgr:

    BEGIN = '\x1b['
    END = 'm'
    RESET = '{}{}'.format(BEGIN, END)

    def __init__(self, parameter, file=sys.stdout):
        self.code = '{}{}{}'.format(sgr.BEGIN, parameter, sgr.END)
        self.file = file

    def __enter__(self):
        self.file.write(self.code)

    def __exit__(self, type, value, traceback):
        self.file.write(sgr.RESET)
