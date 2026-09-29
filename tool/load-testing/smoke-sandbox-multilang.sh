#!/usr/bin/env bash
set -euo pipefail

image="${SANDBOX_IMAGE:-syncode/oj-sandbox-multilang:1.0.0}"
memory="${SANDBOX_MEMORY_LIMIT:-100m}"
workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT

cat > "$workdir/Main.java" <<'JAVA'
import java.util.Scanner;
public class Main {
    public static void main(String[] args) {
        Scanner in = new Scanner(System.in);
        System.out.println(in.nextInt() + in.nextInt());
    }
}
JAVA

cat > "$workdir/Main.cpp" <<'CPP'
#include <iostream>
int main() {
    int a, b;
    std::cin >> a >> b;
    std::cout << a + b << '\n';
}
CPP

cat > "$workdir/main.py" <<'PYTHON'
a, b = map(int, input().split())
print(a + b)
PYTHON

cat > "$workdir/main.go" <<'GO'
package main
import "fmt"
func main() {
    var a, b int
    fmt.Scan(&a, &b)
    fmt.Println(a + b)
}
GO

run_case() {
    local language="$1"
    local command="$2"
    local actual
    local started_at=$SECONDS
    actual="$(docker run --rm \
        --network none --read-only \
        --tmpfs /tmp:rw,noexec,nosuid,size=64m \
        --memory "$memory" --memory-swap "$memory" \
        --cpus 1 --pids-limit 64 \
        --mount "type=bind,src=$workdir,dst=/usr/share/java" \
        "$image" sh -c "$command")"
    if [[ "$actual" != "3" ]]; then
        echo "$language: expected 3, got: $actual" >&2
        exit 1
    fi
    echo "$language: passed ($memory, $((SECONDS - started_at))s)"
        rm -rf "$workdir"/*.class "$workdir"/main "$workdir"/__pycache__
}

run_case java 'javac /usr/share/java/Main.java && printf "1 2\n" | java -cp /usr/share/java Main'
run_case cpp 'g++ -O2 -std=c++17 -pipe /usr/share/java/Main.cpp -o /usr/share/java/main && printf "1 2\n" | /usr/share/java/main'
run_case python 'python3 -m py_compile /usr/share/java/main.py && printf "1 2\n" | python3 -B /usr/share/java/main.py'
run_case go 'GOCACHE=/tmp/go-cache go build -trimpath -o /usr/share/java/main /usr/share/java/main.go && printf "1 2\n" | /usr/share/java/main'
