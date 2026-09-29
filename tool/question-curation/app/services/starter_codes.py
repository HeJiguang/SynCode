"""Per-language starter programs for the multi-language judge pool.

Mirrors com.sintao.common.core.utils.MultiLanguageStarterCodes on the Java side so
direct-database imports expose the same four languages as the backend-generated ones.
"""

from __future__ import annotations

import json

JAVA_TEMPLATE = """import java.io.*;
import java.util.*;

public class Main {
    public static void main(String[] args) throws Exception {
        BufferedReader reader = new BufferedReader(new InputStreamReader(System.in));
        // TODO: parse the input, implement the algorithm, and print the answer.
    }
}"""

CPP_TEMPLATE = """#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    // TODO: parse stdin, implement the algorithm, and print the answer.
    return 0;
}"""

PYTHON_TEMPLATE = """import sys

def solve():
    # TODO: parse stdin, implement the algorithm, and print the answer.
    pass

if __name__ == "__main__":
    solve()"""

GO_TEMPLATE = """package main

import (
    "bufio"
    "fmt"
    "os"
)

func main() {
    in := bufio.NewReader(os.Stdin)
    out := bufio.NewWriter(os.Stdout)
    defer out.Flush()
    _, _ = in, fmt.Fprint
    // TODO: parse stdin, implement the algorithm, and print the answer.
}"""


def build_starter_code(java_starter: str | None) -> dict[str, str]:
    """Expand a legacy Java starter into starter programs for every judge-pool language."""
    java = (java_starter or "").strip() or JAVA_TEMPLATE
    return {
        "java": java,
        "cpp": CPP_TEMPLATE,
        "python": PYTHON_TEMPLATE,
        "go": GO_TEMPLATE,
    }


def build_starter_code_json(java_starter: str | None) -> str:
    return json.dumps(build_starter_code(java_starter))
