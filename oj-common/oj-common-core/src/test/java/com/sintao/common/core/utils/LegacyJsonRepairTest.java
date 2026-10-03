package com.sintao.common.core.utils;

import cn.hutool.json.JSONUtil;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class LegacyJsonRepairTest {

    @Test
    void shouldEscapeRawNewlinesInsideStringValues() {
        String legacy = "[{\"input\":\"5\n1 3 5 7 9\n7\",\"output\":\"3\"}]";

        assertThrows(Exception.class, () -> JSONUtil.toList(legacy, CaseRow.class));

        List<CaseRow> parsed = JSONUtil.toList(
                LegacyJsonRepair.escapeControlCharsInStrings(legacy), CaseRow.class);

        assertEquals(1, parsed.size());
        assertEquals("5\n1 3 5 7 9\n7", parsed.get(0).getInput());
        assertEquals("3", parsed.get(0).getOutput());
    }

    @Test
    void shouldKeepValidJsonAndPrettyPrintedLayoutsUnchanged() {
        String pretty = "[\n  {\n    \"input\": \"1 2\",\n    \"output\": \"3\"\n  }\n]";

        assertEquals(pretty, LegacyJsonRepair.escapeControlCharsInStrings(pretty));
        assertEquals("[]", LegacyJsonRepair.escapeControlCharsInStrings("[]"));
    }

    @Test
    void shouldHandleEscapedSequencesAndTabs() {
        String legacy = "[{\"input\":\"a\\nb\tc\rd\",\"output\":\"x\"}]";

        String repaired = LegacyJsonRepair.escapeControlCharsInStrings(legacy);

        List<CaseRow> parsed = JSONUtil.toList(repaired, CaseRow.class);
        assertEquals("a\nb\tc\rd", parsed.get(0).getInput());
    }

    @Test
    void shouldTolerateNullAndEmptyInput() {
        assertEquals(null, LegacyJsonRepair.escapeControlCharsInStrings(null));
        assertEquals("", LegacyJsonRepair.escapeControlCharsInStrings(""));
    }

    public static class CaseRow {
        private String input;
        private String output;

        public String getInput() {
            return input;
        }

        public void setInput(String input) {
            this.input = input;
        }

        public String getOutput() {
            return output;
        }

        public void setOutput(String output) {
            this.output = output;
        }
    }
}
