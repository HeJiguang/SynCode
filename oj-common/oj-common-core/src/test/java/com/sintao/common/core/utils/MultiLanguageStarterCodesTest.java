package com.sintao.common.core.utils;

import cn.hutool.json.JSONUtil;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class MultiLanguageStarterCodesTest {

    @Test
    void buildStarterMapShouldKeepAuthoredJavaStarter() {
        Map<String, String> starters = MultiLanguageStarterCodes.buildStarterMap("class Authored {}");

        assertEquals(4, starters.size());
        assertEquals("class Authored {}", starters.get(MultiLanguageStarterCodes.JAVA));
        assertTrue(starters.get(MultiLanguageStarterCodes.CPP).contains("int main"));
        assertTrue(starters.get(MultiLanguageStarterCodes.PYTHON).contains("def solve"));
        assertTrue(starters.get(MultiLanguageStarterCodes.GO).contains("func main"));
    }

    @Test
    void buildStarterMapShouldFallBackToGenericJavaTemplateWhenBlank() {
        Map<String, String> starters = MultiLanguageStarterCodes.buildStarterMap("  ");

        assertEquals(4, starters.size());
        assertFalse(starters.get(MultiLanguageStarterCodes.JAVA).isBlank());
        assertTrue(starters.get(MultiLanguageStarterCodes.JAVA).contains("class Main"));
    }

    @Test
    void buildStarterJsonShouldRoundTripThroughParser() {
        String json = MultiLanguageStarterCodes.buildStarterJson("class Authored {}");

        Map<String, String> parsed = JSONUtil.toBean(json, Map.class);
        assertEquals(4, parsed.size());
        assertEquals("class Authored {}", parsed.get("java"));
    }

    @Test
    void expandStarterMapShouldFillMissingLanguagesAndKeepAuthoredEntries() {
        Map<String, String> expanded = MultiLanguageStarterCodes.expandStarterMap(
                Map.of(MultiLanguageStarterCodes.JAVA, "class Authored {}",
                        MultiLanguageStarterCodes.CPP, "int authored() {}"));

        assertEquals(4, expanded.size());
        assertEquals("class Authored {}", expanded.get(MultiLanguageStarterCodes.JAVA));
        assertEquals("int authored() {}", expanded.get(MultiLanguageStarterCodes.CPP));
        assertTrue(expanded.get(MultiLanguageStarterCodes.PYTHON).contains("def solve"));
        assertTrue(expanded.get(MultiLanguageStarterCodes.GO).contains("func main"));
    }

    @Test
    void expandStarterMapShouldReplaceBlankEntriesWithTemplatesAndDropUnknownKeys() {
        Map<String, String> expanded = MultiLanguageStarterCodes.expandStarterMap(
                Map.of(MultiLanguageStarterCodes.JAVA, "class Authored {}",
                        MultiLanguageStarterCodes.PYTHON, "   ",
                        "javascript", "console.log('x')"));

        assertEquals(4, expanded.size());
        assertFalse(expanded.containsKey("javascript"));
        assertTrue(expanded.get(MultiLanguageStarterCodes.PYTHON).contains("def solve"));
        assertTrue(expanded.get(MultiLanguageStarterCodes.CPP).contains("int main"));
        assertTrue(expanded.get(MultiLanguageStarterCodes.GO).contains("func main"));
    }

    @Test
    void expandStarterMapShouldTolerateNullInput() {
        Map<String, String> expanded = MultiLanguageStarterCodes.expandStarterMap(null);

        assertEquals(4, expanded.size());
        assertTrue(expanded.get(MultiLanguageStarterCodes.JAVA).contains("class Main"));
    }
}
