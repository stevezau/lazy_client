import os
import re
import subprocess
import sys
from easy_extract.archive import Archive

EXTENSIONS = [re.compile('.r\d{2}$', re.I),
              re.compile('.part\d+.rar$', re.I),
              re.compile('.rar$', re.I)]

class RarArchive(Archive):
    """The Rar format Archive"""
    ALLOWED_EXTENSIONS = EXTENSIONS

    def _extract(self):
        if '%s.rar' % self.name in self.archives:
            first_archive = self.get_command_filename('%s.rar' % self.name)
        else:
            first_archive = self.get_command_filename(self.archives[0])

        base, __ = os.path.split(first_archive)

        errCode = subprocess.call('cd ' + base + ' ; unrar -o- x ' + first_archive + ' > /dev/null', shell=True)

        return errCode

        