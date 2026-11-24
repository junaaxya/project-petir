#!/usr/bin/env python3
"""Fail CI when a pytest JUnit report has no tests or contains skips."""

from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path


def validate(report: Path) -> None:
    root = ET.parse(report).getroot()
    cases = list(root.iter("testcase"))
    skipped = sum(1 for case in cases if case.find("skipped") is not None)

    print(f"JUnit report: tests={len(cases)} skipped={skipped}")
    if not cases:
        raise RuntimeError("no tests were collected")
    if skipped:
        raise RuntimeError("skipped tests are not allowed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    validate(args.report)


if __name__ == "__main__":
    main()
