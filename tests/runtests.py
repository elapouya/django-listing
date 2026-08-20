#!/usr/bin/env python
#
# Standalone test runner : python tests/runtests.py [test labels...]
#
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")

import django
from django.test.utils import get_runner
from django.conf import settings


def main():
    django.setup()
    runner = get_runner(settings)(verbosity=2, interactive=False)
    labels = sys.argv[1:] or ["tests"]
    sys.exit(bool(runner.run_tests(labels)))


if __name__ == "__main__":
    main()
