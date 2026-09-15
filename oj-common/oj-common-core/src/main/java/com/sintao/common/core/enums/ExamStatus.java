package com.sintao.common.core.enums;

import java.util.Arrays;
import java.util.EnumSet;
import java.util.Set;

public enum ExamStatus {
    DRAFT(0),
    PUBLISHED(1),
    ACTIVE(2),
    FINISHED(3),
    RESULT_RELEASED(4),
    CANCELLED(5);

    private final int code;

    ExamStatus(int code) {
        this.code = code;
    }

    public int getCode() {
        return code;
    }

    public static ExamStatus fromCode(Integer code) {
        if (code == null) {
            throw new IllegalArgumentException("Exam status cannot be null");
        }
        return Arrays.stream(values())
                .filter(status -> status.code == code)
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("Unknown exam status: " + code));
    }

    public boolean canTransitionTo(ExamStatus target) {
        if (target == null || target == this) {
            return false;
        }
        return allowedTargets().contains(target);
    }

    public boolean isTerminal() {
        return this == RESULT_RELEASED || this == CANCELLED;
    }

    private Set<ExamStatus> allowedTargets() {
        return switch (this) {
            case DRAFT -> EnumSet.of(PUBLISHED);
            case PUBLISHED -> EnumSet.of(DRAFT, ACTIVE, CANCELLED);
            case ACTIVE -> EnumSet.of(FINISHED, CANCELLED);
            case FINISHED -> EnumSet.of(RESULT_RELEASED);
            case RESULT_RELEASED, CANCELLED -> EnumSet.noneOf(ExamStatus.class);
        };
    }
}
