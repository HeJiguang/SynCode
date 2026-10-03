package com.sintao.common.core.utils;

/**
 * Repairs legacy JSON documents whose string values contain raw control characters.
 * <p>
 * Strict JSON forbids unescaped control characters inside string literals, but rows written
 * through legacy import paths (for example multi-line judge cases) carry real newlines, which
 * makes strict parsers such as hutool throw {@code Unterminated string}. Escaping those bytes
 * inside string literals restores the document without touching anything outside strings, so
 * already-valid JSON — including pretty-printed layouts — passes through unchanged.
 */
public final class LegacyJsonRepair {

    private LegacyJsonRepair() {
    }

    /**
     * Escapes raw control characters found inside JSON string literals.
     * Text outside strings (structure and whitespace) is returned byte-for-byte.
     */
    public static String escapeControlCharsInStrings(String json) {
        if (json == null || json.isEmpty()) {
            return json;
        }
        StringBuilder repaired = new StringBuilder(json.length() + 16);
        boolean inString = false;
        for (int i = 0; i < json.length(); i++) {
            char current = json.charAt(i);
            if (!inString) {
                if (current == '"') {
                    inString = true;
                }
                repaired.append(current);
                continue;
            }
            if (current == '\\') {
                repaired.append(current);
                if (i + 1 < json.length()) {
                    repaired.append(json.charAt(++i));
                }
                continue;
            }
            if (current == '"') {
                inString = false;
                repaired.append(current);
                continue;
            }
            switch (current) {
                case '\n' -> repaired.append("\\n");
                case '\r' -> repaired.append("\\r");
                case '\t' -> repaired.append("\\t");
                case '\b' -> repaired.append("\\b");
                case '\f' -> repaired.append("\\f");
                default -> {
                    if (current < 0x20) {
                        repaired.append(String.format("\\u%04x", (int) current));
                    } else {
                        repaired.append(current);
                    }
                }
            }
        }
        return repaired.toString();
    }
}
