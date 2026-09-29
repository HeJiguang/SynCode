package com.sintao.common.core.enums;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class ProgramTypeTest {

    @Test
    void preservesExistingIdsAndAddsPythonWithoutRenumberingGo() {
        assertEquals(0, ProgramType.JAVA.getValue());
        assertEquals(1, ProgramType.CPP.getValue());
        assertEquals(2, ProgramType.GOLANG.getValue());
        assertEquals(3, ProgramType.PYTHON.getValue());
    }

    @Test
    void resolvesWireValuesAndLanguageCodes() {
        assertEquals(ProgramType.CPP, ProgramType.fromValue(1));
        assertEquals(ProgramType.GOLANG, ProgramType.fromLanguageCode("GO"));
        assertEquals(ProgramType.PYTHON, ProgramType.fromLanguageCode("python"));
        assertThrows(IllegalArgumentException.class, () -> ProgramType.fromValue(99));
        assertThrows(IllegalArgumentException.class, () -> ProgramType.fromLanguageCode("javascript"));
    }
}
