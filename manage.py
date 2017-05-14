#!venv/bin/python
import os
import sys

# Root path
base_path = os.path.dirname(os.path.abspath(__file__))

# Insert local directories into path
sys.path.insert(0, os.path.join(base_path, 'libs'))

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lazy_client.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

