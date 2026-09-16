package com.sintao.common.core.enums;

import java.util.Locale;
import java.util.Set;

public enum QuestionType {
    PROGRAMMING("CODE", true, false),
    SINGLE_CHOICE("CHOICE", false, true),
    MULTIPLE_CHOICE("CHOICE", false, true),
    TRUE_FALSE("BOOLEAN", false, true),
    FILL_BLANK("TEXT", false, true),
    SHORT_ANSWER("TEXT", false, false),
    SQL("SQL", false, false),
    FILE("FILE", false, false),
    PROJECT("PROJECT", false, false);

    private final String answerType;
    private final boolean judgeSubmission;
    private final boolean objective;

    QuestionType(String answerType, boolean judgeSubmission, boolean objective) {
        this.answerType = answerType;
        this.judgeSubmission = judgeSubmission;
        this.objective = objective;
    }

    public String getAnswerType() { return answerType; }
    public boolean requiresJudgeSubmission() { return judgeSubmission; }
    public boolean isObjective() { return objective; }

    public static QuestionType from(String value) {
        if (value == null || value.isBlank()) return PROGRAMMING;
        return valueOf(value.trim().toUpperCase(Locale.ROOT));
    }

    public static Set<String> names() {
        return Set.of(PROGRAMMING.name(), SINGLE_CHOICE.name(), MULTIPLE_CHOICE.name(), TRUE_FALSE.name(),
                FILL_BLANK.name(), SHORT_ANSWER.name(), SQL.name(), FILE.name(), PROJECT.name());
    }
}
