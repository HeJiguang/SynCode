#!/usr/bin/env python3

"""Install SynCode governance routes into a compatible Hermes API server."""

from __future__ import annotations

import ast
from pathlib import Path
import sys


IMPORT_ANCHOR = "from gateway.platforms import api_server_runs as _api_runs\n"
IMPORT_LINE = "from gateway.platforms import api_server_syncode_governance as _syncode_governance\n"
ROUTE_ANCHOR = "        routes.extend(_api_runs._http_routes(self))\n"
ROUTE_LINE = "        routes.extend(_syncode_governance._http_routes(self))\n"


def _functions(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _require_functions(path: Path, names: set[str]) -> None:
    missing = names - _functions(path)
    if missing:
        raise RuntimeError(f"Hermes compatibility check failed for {path}: missing {sorted(missing)}")


def _require_class_methods(path: Path, class_name: str, names: set[str]) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    class_node = next(
        (node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name),
        None,
    )
    methods = {
        node.name
        for node in (class_node.body if class_node is not None else [])
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    missing = names - methods
    if missing:
        raise RuntimeError(
            f"Hermes compatibility check failed for {path}:{class_name}: missing {sorted(missing)}"
        )


def patch(
    api_server_path: Path,
    write_approval_path: Path,
    memory_tool_path: Path,
    approval_path: Path,
    context_compressor_path: Path,
    approval_context_path: Path,
    approval_wait_path: Path,
    session_messages_path: Path,
) -> bool:
    _require_functions(write_approval_path, {"list_pending", "get_pending", "discard_pending"})
    _require_functions(memory_tool_path, {"load_on_disk_store", "apply_memory_pending"})
    _require_functions(approval_path, {"_gateway_notify_cb", "resolve_gateway_approval"})
    _require_class_methods(
        context_compressor_path,
        "ContextCompressor",
        {"__init__", "compress", "_generate_summary", "_strip_summary_prefix", "_with_summary_prefix"},
    )
    _require_functions(approval_context_path, {"get_current_session_key"})
    _require_functions(approval_wait_path, {"_await_gateway_decision"})
    _require_class_methods(session_messages_path, "SessionMessagesMixin", {"get_active_message_watermark"})

    source = api_server_path.read_text(encoding="utf-8")
    if IMPORT_LINE in source and ROUTE_LINE in source:
        print("SynCode Hermes governance API patch already applied")
        return False
    if IMPORT_LINE in source or ROUTE_LINE in source:
        raise RuntimeError("Hermes governance API is only partially patched")
    if source.count(IMPORT_ANCHOR) != 1 or source.count(ROUTE_ANCHOR) != 1:
        raise RuntimeError("Hermes API server layout changed; review the governance patch before building")

    source = source.replace(IMPORT_ANCHOR, IMPORT_ANCHOR + IMPORT_LINE)
    source = source.replace(ROUTE_ANCHOR, ROUTE_ANCHOR + ROUTE_LINE)
    ast.parse(source)
    api_server_path.write_text(source, encoding="utf-8")
    print("Installed SynCode Hermes governance API routes")
    return True


def main() -> None:
    if len(sys.argv) != 9:
        raise SystemExit(
            f"usage: {sys.argv[0]} API_SERVER_PATH WRITE_APPROVAL_PATH MEMORY_TOOL_PATH "
            "APPROVAL_PATH CONTEXT_COMPRESSOR_PATH APPROVAL_CONTEXT_PATH APPROVAL_WAIT_PATH "
            "SESSION_MESSAGES_PATH"
        )
    patch(*(Path(value) for value in sys.argv[1:]))


if __name__ == "__main__":
    main()
