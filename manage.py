#!/usr/bin/env python
"""Las tareas de Django del servidor, como `python manage.py migrate`."""

import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'brilliant_servidor.settings')
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
