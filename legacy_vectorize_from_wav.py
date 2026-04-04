#!/usr/bin/env python3
"""
Legacy wrapper: maps ``--input-wav`` to ``vectorize --input-audio``.

Prefer: ``python3 pvrr_cli.py vectorize --input-audio …`` or ``python3 -m pvrr vectorize …``.
"""

from __future__ import annotations

import sys

from pvrr.command_line import main


if __name__ == "__main__":
    translated = []
    args = sys.argv[1:]
    for arg in args:
        if arg == "--input-wav":
            translated.append("--input-audio")
        else:
            translated.append(arg)
    main(["vectorize", *translated])
