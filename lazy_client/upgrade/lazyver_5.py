__author__ = 'steve'
import os
import subprocess
from lazy_client_core.utils.common import green_color, fail_color, blue_color

def upgrade():
    if os.getuid() == 0:
        run_command(['/usr/bin/env', 'easy_install', '--upgrade', 'http://drifthost.com/lazy_common-0.1-py2.7.egg'], check=True)
    else:
        run_command(['/usr/bin/env', 'sudo', '/usr/bin/env', 'easy_install', 'http://drifthost.com/lazy_common-0.1-py2.7.egg'], check=True)

def run_command(cmd, check=False):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    return_code = p.returncode

    if check:
        if return_code != 0:
            print out
            print err
            print fail_color("Error running command %s" % cmd)
            exit(1)

    return return_code, out, err
