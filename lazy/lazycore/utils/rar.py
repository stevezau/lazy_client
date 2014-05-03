import os
import re
import subprocess
import sys
from easy_extract.archive import Archive
import logging

EXTENSIONS = [re.compile('.r\d{2}$', re.I),
              re.compile('.part\d+.rar$', re.I),
              re.compile('.rar$', re.I)]

logger = logging.getLogger(__name__)

class RarArchive(Archive):
    """The Rar format Archive"""
    ALLOWED_EXTENSIONS = EXTENSIONS

    def get_first_archive(self):
        if '%s.rar' % self.name in self.archives:
            first_archive = self.get_command_filename('%s.rar' % self.name)
        else:
            first_archive = self.get_command_filename(self.archives[0])

        return first_archive

    def _extract(self):

        first_archive = self.get_first_archive()

        base, __ = os.path.split(first_archive)

        errCode = subprocess.call('cd ' + base + ' ; unrar -o- x ' + first_archive + ' > /dev/null', shell=True)

        return errCode

    def crc(self, file_name):
        import zlib
        prev=0

        ##for the script to work on any sfv file no matter where it's located , we have to parse the absolute path of each file within sfv
        ##so, we will add the file path to each file name , pretty neat huh ?
        fileName=os.path.join(file_name)

        #print fileName
        if os.path.exists(fileName):
            store=open(fileName, "rb")
            for eachLine in store:
                prev = zlib.crc32(eachLine, prev)
            return "%x"%(prev & 0xFFFFFFFF)
            store.close()

    def crc_check(self):

        bad_archives = []

        sfv_file_name = "%s.sfv" % self.name
        sfv_file = os.path.join(self.path, sfv_file_name)
        check_sfv = False

        if os.path.isfile(sfv_file):

            if os.path.getsize(sfv_file) == 0:
                logger.debug("Empty SFV file found, won't check via SFV: %s" % sfv_file)
            else:
                check_sfv = True

            if check_sfv:
                logger.debug("Checking CRC against SFV file: %s" % sfv_file)

                names_list = []
                sfv_list = []

                s = open(sfv_file)

                ##loop thru all lines of sfv, removes all unnecessary /r /n chars, split each line to two values,creates two distinct arrays
                for line in s.readlines():
                    if line.startswith(';'):
                        continue
                    m=line.rstrip('\r\n')
                    m=m.split(' ')
                    names_list.append(m[0])
                    sfv_list.append(m[1])

                i = 0

                while(len(names_list)>i):
                    file_path = os.path.join(self.path, names_list[i])
                    calc_sfv_value=self.crc(file_path)

                    if sfv_list[i].lstrip('0')==calc_sfv_value:
                        logger.debug("CRC check passed: %s" % file_path)
                        pass
                    else:
                        logger.debug("CRC check failed: %s " % file_path)
                        bad_archives.append(file_path)

                    i = i+1

        if not check_sfv:

            first_archive = self.get_first_archive()
            base, __ = os.path.split(first_archive)

            p = subprocess.Popen(["unrar", "t", first_archive], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            out, err = p.communicate()

            for line in err.splitlines():
                if line.startswith("ERROR: Bad archive"):
                    #found a bad archive
                    archive = line.replace("ERROR: Bad archive ", "")
                    bad_archives.append(archive)
                elif line.startswith("Cannot find volume "):
                    archive = line.replace("Cannot find volume ", "")
                    bad_archives.append(archive)

        return bad_archives
