package com.sintao.judge.domain;

import com.sintao.common.core.enums.ProgramType;

import java.util.Arrays;

import static com.sintao.common.core.constants.JudgeConstants.DOCKER_USER_CODE_DIR;

public enum JudgeLanguageDefinition {

    JAVA(
            ProgramType.JAVA,
            "Main.java",
            1,
            new String[]{"javac", DOCKER_USER_CODE_DIR + "/Main.java"},
            new String[]{"java", "-cp", DOCKER_USER_CODE_DIR, "Main"}
    ),
    CPP(
            ProgramType.CPP,
            "Main.cpp",
            1,
            new String[]{"g++", "-O2", "-std=c++17", "-pipe", DOCKER_USER_CODE_DIR + "/Main.cpp",
                    "-o", DOCKER_USER_CODE_DIR + "/main"},
            new String[]{DOCKER_USER_CODE_DIR + "/main"}
    ),
    GOLANG(
            ProgramType.GOLANG,
            "main.go",
            30,
            new String[]{"env", "GOCACHE=/tmp/go-cache",
                    "go", "build", "-trimpath", "-o", DOCKER_USER_CODE_DIR + "/main",
                    DOCKER_USER_CODE_DIR + "/main.go"},
            new String[]{DOCKER_USER_CODE_DIR + "/main"}
    ),
    PYTHON(
            ProgramType.PYTHON,
            "main.py",
            1,
            new String[]{"python3", "-m", "py_compile", DOCKER_USER_CODE_DIR + "/main.py"},
            new String[]{"python3", "-B", DOCKER_USER_CODE_DIR + "/main.py"}
    );

    private final ProgramType programType;
    private final String sourceFileName;
    private final long minimumCompileSeconds;
    private final String[] compileCommand;
    private final String[] runCommand;

    JudgeLanguageDefinition(ProgramType programType, String sourceFileName, long minimumCompileSeconds,
                            String[] compileCommand, String[] runCommand) {
        this.programType = programType;
        this.sourceFileName = sourceFileName;
        this.minimumCompileSeconds = minimumCompileSeconds;
        this.compileCommand = compileCommand;
        this.runCommand = runCommand;
    }

    public ProgramType programType() {
        return programType;
    }

    public String sourceFileName() {
        return sourceFileName;
    }

    public long minimumCompileSeconds() {
        return minimumCompileSeconds;
    }

    public String[] compileCommand() {
        return Arrays.copyOf(compileCommand, compileCommand.length);
    }

    public String[] runCommand() {
        return Arrays.copyOf(runCommand, runCommand.length);
    }

    public static JudgeLanguageDefinition fromProgramType(Integer programType) {
        ProgramType resolved = ProgramType.fromValue(programType);
        return Arrays.stream(values())
                .filter(definition -> definition.programType == resolved)
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("Unsupported program type: " + programType));
    }
}
