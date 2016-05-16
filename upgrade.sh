#!/usr/bin/env bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
/usr/local/bin/pip install --upgrade flexget
su - media -c "$DIR/lazy.sh restart"
