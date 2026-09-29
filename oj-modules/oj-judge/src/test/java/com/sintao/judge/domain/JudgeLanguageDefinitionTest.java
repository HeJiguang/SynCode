package com.sintao.judge.domain;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class JudgeLanguageDefinitionTest {

    @Test
    void mapsEverySupportedProgramTypeToFixedCommands() {
        assertEquals("Main.java", JudgeLanguageDefinition.fromProgramType(0).sourceFileName());
        assertArrayEquals(new String[]{"/usr/share/java/main"},
                JudgeLanguageDefinition.fromProgramType(1).runCommand());
        assertEquals("main.go", JudgeLanguageDefinition.fromProgramType(2).sourceFileName());
        assertEquals(30, JudgeLanguageDefinition.fromProgramType(2).minimumCompileSeconds());
        assertArrayEquals(new String[]{"env", "GOCACHE=/tmp/go-cache", "go", "build", "-trimpath",
                "-o", "/usr/share/java/main", "/usr/share/java/main.go"},
                JudgeLanguageDefinition.fromProgramType(2).compileCommand());
        assertArrayEquals(new String[]{"python3", "-B", "/usr/share/java/main.py"},
                JudgeLanguageDefinition.fromProgramType(3).runCommand());
    }

    @Test
    void rejectsUnknownProgramTypeBeforeCreatingACommand() {
        assertThrows(IllegalArgumentException.class,
                () -> JudgeLanguageDefinition.fromProgramType(99));
    }
}
