"""Export the field catalog to JSON.

The backend catalog (catalog.py) is the single source of truth. This script
serializes it so the OpenResty engine and the docs can consume the exact same
field metadata (keys / value types / requires_arg / operators). Run:

    python -m app.fields.export [output_path]

Default output: engine/lua/waf/fields_catalog.json (relative to repo root).
"""
from __future__ import annotations

import json
import os
import sys

from app.fields.catalog import FIELDS, OPERATORS, OPERATORS_BY_TYPE


def build() -> dict:
    return {
        "version": 1,
        "fields": FIELDS,
        "operators": OPERATORS,
        "operators_by_type": OPERATORS_BY_TYPE,
    }


def main() -> None:
    if len(sys.argv) > 1:
        out = sys.argv[1]
    else:
        repo_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..")
        )
        out = os.path.join(repo_root, "engine", "lua", "waf", "fields_catalog.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(build(), f, ensure_ascii=False, indent=2)
    print(f"wrote {len(FIELDS)} fields -> {out}")


if __name__ == "__main__":
    main()
