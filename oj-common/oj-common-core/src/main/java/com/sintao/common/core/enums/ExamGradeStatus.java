package com.sintao.common.core.enums;

import java.util.Arrays;

public enum ExamGradeStatus {
    WAITING_FOR_JUDGE(0),
    READY(1),
    RELEASED(2),
    NEEDS_REVIEW(3);

    private final int code;

    ExamGradeStatus(int code) {
        this.code = code;
    }

    public int getCode() {
        return code;
    }

    public static ExamGradeStatus fromCode(Integer code) {
        if (code == null) {
            throw new IllegalArgumentException("Exam grade status cannot be null");
        }
        return Arrays.stream(values())
                .filter(status -> status.code == code)
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("Unknown exam grade status: " + code));
    }
}
