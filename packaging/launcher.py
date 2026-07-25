"""Точка входа для собранного приложения.

PyInstaller не умеет запускать пакет как ``python -m qlizmet``, поэтому нужен
отдельный скрипт, который просто зовёт ту же функцию ``main``.
"""
import sys

from qlizmet.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
