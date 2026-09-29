package com.sintao.common.core.utils;

import cn.hutool.core.util.StrUtil;
import cn.hutool.json.JSONUtil;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Builds the per-language starter programs shared by the question bank and the multi-language judge pool.
 * <p>
 * The judge sandbox accepts java/cpp/python/go, so every PROGRAMMING question must expose a starter
 * for each of them even when it was authored with a legacy Java-only {@code default_code}.
 */
public final class MultiLanguageStarterCodes {

    public static final String JAVA = "java";
    public static final String CPP = "cpp";
    public static final String PYTHON = "python";
    public static final String GO = "go";

    public static final List<String> LANGUAGE_KEYS = List.of(JAVA, CPP, PYTHON, GO);

    private static final String JAVA_TEMPLATE = """
            import java.io.*;
            import java.util.*;

            public class Main {
                public static void main(String[] args) throws Exception {
                    BufferedReader reader = new BufferedReader(new InputStreamReader(System.in));
                    // TODO: parse the input, implement the algorithm, and print the answer.
                }
            }""";

    private static final String CPP_TEMPLATE = """
            #include <bits/stdc++.h>
            using namespace std;

            int main() {
                ios::sync_with_stdio(false);
                cin.tie(nullptr);
                // TODO: parse stdin, implement the algorithm, and print the answer.
                return 0;
            }""";

    private static final String PYTHON_TEMPLATE = """
            import sys

            def solve():
                # TODO: parse stdin, implement the algorithm, and print the answer.
                pass

            if __name__ == "__main__":
                solve()""";

    private static final String GO_TEMPLATE = """
            package main

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
            }""";

    private MultiLanguageStarterCodes() {
    }

    /**
     * Expands a legacy Java starter (or a blank one) into starter programs for every judge-pool language.
     * The Java entry keeps the original code so existing questions keep their authored starter.
     */
    public static Map<String, String> buildStarterMap(String javaStarter) {
        Map<String, String> starters = new LinkedHashMap<>();
        starters.put(JAVA, StrUtil.blankToDefault(javaStarter, JAVA_TEMPLATE));
        starters.put(CPP, CPP_TEMPLATE);
        starters.put(PYTHON, PYTHON_TEMPLATE);
        starters.put(GO, GO_TEMPLATE);
        return starters;
    }

    /**
     * Merges authored starters over the full judge-pool language set: authored non-blank entries are
     * kept as-is, missing or blank languages fall back to their canonical TODO template, and unknown
     * keys are dropped. Legacy rows persisted with only {@code {"java": ...}} therefore still expose
     * every language the sandbox accepts.
     */
    public static Map<String, String> expandStarterMap(Map<String, String> authored) {
        Map<String, String> starters = new LinkedHashMap<>();
        starters.put(JAVA, StrUtil.blankToDefault(authored == null ? null : authored.get(JAVA), JAVA_TEMPLATE));
        starters.put(CPP, StrUtil.blankToDefault(authored == null ? null : authored.get(CPP), CPP_TEMPLATE));
        starters.put(PYTHON, StrUtil.blankToDefault(authored == null ? null : authored.get(PYTHON), PYTHON_TEMPLATE));
        starters.put(GO, StrUtil.blankToDefault(authored == null ? null : authored.get(GO), GO_TEMPLATE));
        return starters;
    }

    public static String buildStarterJson(String javaStarter) {
        return JSONUtil.toJsonStr(buildStarterMap(javaStarter));
    }

    public static String javaStarterOrDefault(String javaStarter) {
        return StrUtil.blankToDefault(javaStarter, JAVA_TEMPLATE);
    }
}
