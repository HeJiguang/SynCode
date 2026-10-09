#!/usr/bin/env python3

"""Keep Hermes' skills endpoint compatible with the bundled skills helper."""

from __future__ import annotations

import ast
from pathlib import Path
import sys


BROKEN_CALL = """_find_all_skills(
                    skip_disabled=False, include_editorial=True
                )"""
COMPATIBLE_CALL = "_find_all_skills(skip_disabled=False)"


def _supports_include_editorial(skills_tool_path: Path) -> bool:
    tree = ast.parse(skills_tool_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "_find_all_skills":
            parameters = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
            return any(parameter.arg == "include_editorial" for parameter in parameters)
    raise RuntimeError(f"_find_all_skills was not found in {skills_tool_path}")


def patch(api_server_path: Path, skills_tool_path: Path) -> bool:
    if _supports_include_editorial(skills_tool_path):
        print("Hermes skills API already matches the bundled skills helper")
        return False

    source = api_server_path.read_text(encoding="utf-8")
    broken_count = source.count(BROKEN_CALL)
    compatible_count = source.count(COMPATIBLE_CALL)
    if broken_count == 1:
        api_server_path.write_text(source.replace(BROKEN_CALL, COMPATIBLE_CALL), encoding="utf-8")
        print("Patched Hermes skills API for the bundled skills helper")
        return True
    if broken_count == 0 and compatible_count == 1:
        print("Hermes skills API compatibility patch already applied")
        return False
    raise RuntimeError(
        "Hermes skills API has an unexpected _find_all_skills call; review the upstream image before building"
    )


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(f"usage: {sys.argv[0]} API_SERVER_PATH SKILLS_TOOL_PATH")
    patch(Path(sys.argv[1]), Path(sys.argv[2]))


if __name__ == "__main__":
    main()
