from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from app.config import Settings


@dataclass(slots=True)
class ExecutionResult:
    exit_code: int
    stdout: str
    stderr: str
    elapsed_ms: int


class ExecutionService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def run_java_source(self, *, java_source: str, inputs: list[str], workdir: Path) -> ExecutionResult:
        workdir.mkdir(parents=True, exist_ok=True)
        source_file = workdir / "Solution.java"
        source_file.write_text(java_source, encoding="utf-8")

        compile_process = subprocess.run(
            ["javac", str(source_file.name)],
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if compile_process.returncode != 0:
            return ExecutionResult(
                exit_code=compile_process.returncode,
                stdout=(compile_process.stdout or "").strip(),
                stderr=(compile_process.stderr or "").strip(),
                elapsed_ms=0,
            )

        run_input = ""
        if inputs:
            run_input = "\n".join(inputs)

        started = time.perf_counter()
        run_process = subprocess.run(
            ["java", "Solution"],
            cwd=workdir,
            input=run_input,
            capture_output=True,
            text=True,
            timeout=10,
        )
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        return ExecutionResult(
            exit_code=run_process.returncode,
            stdout=(run_process.stdout or "").strip(),
            stderr=(run_process.stderr or "").strip(),
            elapsed_ms=elapsed_ms,
        )
