package com.sintao.judge.sandbox;

import com.sintao.judge.domain.JudgeLanguageDefinition;
import java.util.List;

/** Commands are server-owned constants. Source code is a file, never interpolated into a shell. */
record GoJudgeLanguage(String source, String artifact, List<String> compile, List<String> run) {
    static GoJudgeLanguage of(Integer type, long memoryBytes) {
        return switch (JudgeLanguageDefinition.fromProgramType(type)) {
            case JAVA -> new GoJudgeLanguage("Main.java", "program.jar",
                    List.of("/bin/sh", "-c", "mkdir classes && javac -J-XX:+UseSerialGC -J-XX:ActiveProcessorCount=1 -encoding UTF-8 -d classes Main.java && jar --create --file program.jar -C classes ."),
                    List.of("/usr/bin/java", "-Xms8m", "-Xmx" + Math.max(8, memoryBytes / 1048576 * 60 / 100) + "m",
                            "-XX:+UseSerialGC", "-XX:ActiveProcessorCount=1", "-XX:ReservedCodeCacheSize=32m",
                            "-cp", "/w/program.jar", "Main"));
            case CPP -> new GoJudgeLanguage("Main.cpp", "program",
                    List.of("/usr/bin/g++", "-O2", "-std=c++17", "-pipe", "Main.cpp", "-o", "program"),
                    List.of("/w/program"));
            case GOLANG -> new GoJudgeLanguage("main.go", "program",
                    List.of("/usr/bin/go", "build", "-trimpath", "-o", "program", "main.go"), List.of("/w/program"));
            case PYTHON -> new GoJudgeLanguage("main.py", "program.pyc",
                    List.of("/usr/bin/python3", "-c", "import py_compile; py_compile.compile('main.py', cfile='program.pyc', doraise=True)"),
                    List.of("/usr/bin/python3", "-B", "/w/program.pyc"));
        };
    }
}
