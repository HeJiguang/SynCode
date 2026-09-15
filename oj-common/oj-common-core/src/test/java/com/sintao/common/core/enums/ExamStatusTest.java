package com.sintao.common.core.enums;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ExamStatusTest {

    @Test
    void preservesLegacyCodesAndResolvesAllStates() {
        assertEquals(ExamStatus.DRAFT, ExamStatus.fromCode(0));
        assertEquals(ExamStatus.PUBLISHED, ExamStatus.fromCode(1));
        assertEquals(ExamStatus.ACTIVE, ExamStatus.fromCode(2));
        assertEquals(ExamStatus.FINISHED, ExamStatus.fromCode(3));
        assertEquals(ExamStatus.RESULT_RELEASED, ExamStatus.fromCode(4));
        assertEquals(ExamStatus.CANCELLED, ExamStatus.fromCode(5));
        assertThrows(IllegalArgumentException.class, () -> ExamStatus.fromCode(null));
        assertThrows(IllegalArgumentException.class, () -> ExamStatus.fromCode(6));
    }

    @Test
    void acceptsOnlyDeclaredLifecycleTransitions() {
        assertTrue(ExamStatus.DRAFT.canTransitionTo(ExamStatus.PUBLISHED));
        assertTrue(ExamStatus.PUBLISHED.canTransitionTo(ExamStatus.DRAFT));
        assertTrue(ExamStatus.PUBLISHED.canTransitionTo(ExamStatus.ACTIVE));
        assertTrue(ExamStatus.PUBLISHED.canTransitionTo(ExamStatus.CANCELLED));
        assertTrue(ExamStatus.ACTIVE.canTransitionTo(ExamStatus.FINISHED));
        assertTrue(ExamStatus.ACTIVE.canTransitionTo(ExamStatus.CANCELLED));
        assertTrue(ExamStatus.FINISHED.canTransitionTo(ExamStatus.RESULT_RELEASED));

        assertFalse(ExamStatus.DRAFT.canTransitionTo(ExamStatus.ACTIVE));
        assertFalse(ExamStatus.ACTIVE.canTransitionTo(ExamStatus.DRAFT));
        assertFalse(ExamStatus.FINISHED.canTransitionTo(ExamStatus.ACTIVE));
        assertFalse(ExamStatus.RESULT_RELEASED.canTransitionTo(ExamStatus.DRAFT));
        assertFalse(ExamStatus.CANCELLED.canTransitionTo(ExamStatus.DRAFT));
        assertFalse(ExamStatus.ACTIVE.canTransitionTo(ExamStatus.ACTIVE));
        assertFalse(ExamStatus.ACTIVE.canTransitionTo(null));
    }

    @Test
    void identifiesTerminalStates() {
        assertTrue(ExamStatus.RESULT_RELEASED.isTerminal());
        assertTrue(ExamStatus.CANCELLED.isTerminal());
        assertFalse(ExamStatus.FINISHED.isTerminal());
    }
}
