package com.sintao.common.core.enums;

import java.util.Arrays;

public enum ExamAttemptStatus {
    IN_PROGRESS(0),
    SUBMITTED(1),
    TIMED_OUT(2),
    CANCELLED(3);

    private final int code;

    ExamAttemptStatus(int code) {
        this.code = code;
    }

    public int getCode() {
        return code;
    }

    public static ExamAttemptStatus fromCode(Integer code) {
        if (code == null) {
            throw new IllegalArgumentException("Exam attempt status cannot be null");
        }
        return Arrays.stream(values())
                .filter(status -> status.code == code)
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("Unknown exam attempt status: " + code));
    }

    public boolean canTransitionTo(ExamAttemptStatus target) {
        return this == IN_PROGRESS && target != null && target != IN_PROGRESS;
    }

    public boolean isTerminal() {
        return this != IN_PROGRESS;
    }
}
