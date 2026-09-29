package com.sintao.common.core.enums;

public enum JudgeTaskType {
    REALTIME,
    BATCH;

    public static JudgeTaskType resolve(JudgeTaskType taskType, Long examId) {
        if (taskType != null) {
            return taskType;
        }
        return examId == null ? REALTIME : BATCH;
    }
}
