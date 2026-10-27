#!/usr/bin/env python3
"""Run on a Linux runner host after deployment; only uses the Python standard library."""
import json
import os
import urllib.request

ENDPOINT = os.environ.get("GO_JUDGE_ENDPOINT", "http://127.0.0.1:5050").rstrip("/")
TOKEN = os.environ["GO_JUDGE_TOKEN"]


def request(path, payload=None, method=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(ENDPOINT + path, data=data, method=method,
                                 headers={"Authorization": "Bearer " + TOKEN,
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=100) as response:
        return response.read()


def delete_results(result):
    for file_id in set(result.get("fileIds", {}).values()):
        request("/file/" + file_id, method="DELETE")


def command(args, stdin="", copy_in=None, cached=None, cpu_ms=2000,
            memory=256 * 1024 * 1024, output=32 * 1024 * 1024):
    return {"args": args,
            "env": ["PATH=/usr/bin:/bin", "HOME=/w", "LANG=C.UTF-8",
                    "GOCACHE=/tmp/go-cache", "GOPATH=/tmp/go", "GOMAXPROCS=1", "GOPROXY=off"],
            "files": [{"content": stdin}, {"name": "stdout", "max": output},
                      {"name": "stderr", "max": 65536}],
            "cpuLimit": cpu_ms * 1000000, "clockLimit": cpu_ms * 3000000,
            "memoryLimit": memory, "procLimit": 64, "cpuRateLimit": 1000,
            "copyIn": copy_in or {}, "copyOutCached": cached or ["stdout"],
            "copyOutMax": max(output, 64 * 1024 * 1024)}


def run(cmd):
    results = json.loads(request("/run", {"cmd": [cmd]}))
    assert len(results) == 1, results
    return results[0]


def stdout(result):
    file_id = result.get("fileIds", {}).get("stdout")
    return request("/file/" + file_id).decode() if file_id else result.get("files", {}).get("stdout", "")


def accepted_output(cmd, expected):
    result = run(cmd)
    try:
        assert result["status"] == "Accepted", result
        assert stdout(result) == expected, result
    finally:
        delete_results(result)


plans = [
    ("Main.java", "program.jar",
     'import java.io.*; public class Main { static class Inner {} '
     'public static void main(String[] args) throws Exception {'
     'new Inner(); System.out.print(new String(System.in.readAllBytes(), "UTF-8"));}}',
     ["/bin/sh", "-c", "mkdir classes && javac -J-XX:+UseSerialGC -J-XX:ActiveProcessorCount=1 -d classes Main.java && jar --create --file program.jar -C classes ."],
     ["/usr/bin/java", "-Xms8m", "-Xmx128m", "-XX:+UseSerialGC", "-XX:ActiveProcessorCount=1", "-cp", "/w/program.jar", "Main"]),
    ("Main.cpp", "program", '#include <iostream>\nint main(){ std::cout << std::cin.rdbuf(); }',
     ["/usr/bin/g++", "-O2", "Main.cpp", "-o", "program"], ["/w/program"]),
    ("main.go", "program", 'package main\nimport("io";"os")\nfunc main(){io.Copy(os.Stdout,os.Stdin)}',
     ["/usr/bin/go", "build", "-trimpath", "-o", "program", "main.go"], ["/w/program"]),
    ("main.py", "program.pyc", "import sys\nsys.stdout.write(sys.stdin.read())\n",
     ["/usr/bin/python3", "-c", "import py_compile; py_compile.compile('main.py', cfile='program.pyc', doraise=True)"],
     ["/usr/bin/python3", "-B", "/w/program.pyc"]),
]

for source, artifact, code, compile_args, run_args in plans:
    compiled = run(command(compile_args, copy_in={source: {"content": code}}, cached=[artifact + "?"],
                           cpu_ms=30000, memory=512 * 1024 * 1024))
    try:
        assert compiled["status"] == "Accepted", compiled
        file_id = compiled["fileIds"][artifact]
        for stdin in ["  keep spaces\n\n", "", "second run\n"]:
            accepted_output(command(run_args, stdin, {artifact: {"fileId": file_id}}), stdin)
    finally:
        delete_results(compiled)
    print("PASS compile once / repeated artifact / stdin EOF:", source)

# Normal exit must reclaim child processes and reset writable areas.
accepted_output(command(["/bin/sh", "-c", "echo leak >/tmp/oj-leak; echo leak >/w/oj-leak; sleep 100 &"]), "")
accepted_output(command(["/bin/sh", "-c", "test ! -e /tmp/oj-leak && test ! -e /w/oj-leak && echo clean"]), "clean\n")
print("PASS normal-exit cleanup")

for args, cpu_ms, output, expected in [
    (["/bin/sh", "-c", "echo leak >/tmp/oj-leak; while :; do :; done"], 100, 1048576, "Time Limit Exceeded"),
    (["/usr/bin/python3", "-c", "while True: print('x'*4096)"], 2000, 1024, "Output Limit Exceeded"),
]:
    result = run(command(args, cpu_ms=cpu_ms, output=output))
    try:
        assert result["status"] == expected, result
    finally:
        delete_results(result)
    accepted_output(command(["/bin/sh", "-c", "test ! -e /tmp/oj-leak && echo clean"]), "clean\n")
    print("PASS", expected, "/ cleanup")

# Pin the runner to one prefork/parallel worker when testing reuse deterministically.
print("All runner smoke checks passed. For deterministic reuse checks, deploy with GO_JUDGE_PARALLELISM=1.")
