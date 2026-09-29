package com.sintao.common.core.enums;

import lombok.Getter;

import java.util.Arrays;

@Getter
public enum ProgramType {

    JAVA(0, "java", "Java 语言"),

    CPP(1, "cpp", "C++ 语言"),

    GOLANG(2, "go", "Go 语言"),

    PYTHON(3, "python", "Python 语言");

    private final Integer value;

    private final String languageCode;

    private final String desc;

    ProgramType(Integer value, String languageCode, String desc) {
        this.value = value;
        this.languageCode = languageCode;
        this.desc = desc;
    }

    public static ProgramType fromValue(Integer value) {
        return Arrays.stream(values())
                .filter(type -> type.value.equals(value))
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("Unsupported program type: " + value));
    }

    public static ProgramType fromLanguageCode(String languageCode) {
        return Arrays.stream(values())
                .filter(type -> type.languageCode.equalsIgnoreCase(languageCode))
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("Unsupported language: " + languageCode));
    }
}
