import sys

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
