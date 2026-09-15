package com.sintao.common.core.enums;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ExamAttemptStatusTest {

    @Test
    void supportsOnlyOneWayTerminalTransitions() {
        assertTrue(ExamAttemptStatus.IN_PROGRESS.canTransitionTo(ExamAttemptStatus.SUBMITTED));
        assertTrue(ExamAttemptStatus.IN_PROGRESS.canTransitionTo(ExamAttemptStatus.TIMED_OUT));
        assertTrue(ExamAttemptStatus.IN_PROGRESS.canTransitionTo(ExamAttemptStatus.CANCELLED));
        assertFalse(ExamAttemptStatus.IN_PROGRESS.canTransitionTo(ExamAttemptStatus.IN_PROGRESS));
        assertFalse(ExamAttemptStatus.SUBMITTED.canTransitionTo(ExamAttemptStatus.TIMED_OUT));
        assertFalse(ExamAttemptStatus.TIMED_OUT.canTransitionTo(ExamAttemptStatus.SUBMITTED));
        assertFalse(ExamAttemptStatus.CANCELLED.canTransitionTo(ExamAttemptStatus.IN_PROGRESS));
    }

    @Test
    void resolvesCodesAndTerminalStates() {
        assertEquals(ExamAttemptStatus.IN_PROGRESS, ExamAttemptStatus.fromCode(0));
        assertEquals(ExamAttemptStatus.SUBMITTED, ExamAttemptStatus.fromCode(1));
        assertEquals(ExamAttemptStatus.TIMED_OUT, ExamAttemptStatus.fromCode(2));
        assertEquals(ExamAttemptStatus.CANCELLED, ExamAttemptStatus.fromCode(3));
        assertFalse(ExamAttemptStatus.IN_PROGRESS.isTerminal());
        assertTrue(ExamAttemptStatus.SUBMITTED.isTerminal());
        assertThrows(IllegalArgumentException.class, () -> ExamAttemptStatus.fromCode(9));
    }
}
