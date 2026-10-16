#!/usr/bin/env python3
"""Fail a Hermes image build if the enabled skills toolset gains write capabilities."""

from __future__ import annotations

import ast
import sys
from pathlib import Path


ALLOWED_TOOLS = {"skills_list", "skill_view"}


def registered_skills_tools(source_path: Path) -> set[str]:
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    tools: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "register"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "registry"
        ):
            continue
        arguments = {
            keyword.arg: keyword.value
            for keyword in node.keywords
            if keyword.arg is not None
        }
        toolset = arguments.get("toolset")
        name = arguments.get("name")
        if (
            isinstance(toolset, ast.Constant)
            and toolset.value == "skills"
            and isinstance(name, ast.Constant)
            and isinstance(name.value, str)
        ):
            tools.add(name.value)
    return tools


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify-hermes-skills-toolset.py <skills_tool.py>")
    source_path = Path(sys.argv[1])
    actual = registered_skills_tools(source_path)
    if actual != ALLOWED_TOOLS:
        raise RuntimeError(
            "Hermes skills toolset contract changed: "
            f"expected {sorted(ALLOWED_TOOLS)}, found {sorted(actual)}"
        )
    print(f"Hermes skills toolset is read-only: {', '.join(sorted(actual))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
