#!/bin/bash

git pull
python manage.py migrate
python manage.py sitetreeload --mode=replace /home/media/lazy/lazyweb/fixtures/lazyweb_initialdata.json
python manage.py collectstatic