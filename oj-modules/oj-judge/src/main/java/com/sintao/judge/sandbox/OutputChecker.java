package com.sintao.judge.sandbox;

import com.alibaba.fastjson2.JSON;
import com.fasterxml.jackson.core.JsonFactory;
import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.core.JsonToken;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.function.Consumer;

/** Complete output is checked before any diagnostic preview is truncated. */
public final class OutputChecker {
    private OutputChecker() { }

    public static String resolve(String config) {
        String type = config == null || config.isBlank() ? "text" : JSON.parseObject(config).getString("checker");
        if (type == null) type = "text";
        if (!Set.of("text", "exact", "tokens", "unorderedLines", "unorderedTriples").contains(type)) {
            throw new IllegalArgumentException("Unsupported output checker: " + type);
        }
        return type;
    }

    public static boolean check(String type, String expected, Path actual, long deadline) throws IOException {
        budget(deadline);
        if (expected == null) return true;
        boolean passed = switch (type) {
            case "exact" -> expected.equals(Files.readString(actual));
            case "text" -> normalize(expected).equals(normalize(Files.readString(actual)));
            case "tokens" -> tokens(expected, actual, deadline);
            case "unorderedLines" -> lines(expected, actual, deadline);
            case "unorderedTriples" -> triples(expected, actual, deadline);
            default -> throw new IllegalArgumentException("Unsupported output checker: " + type);
        };
        budget(deadline);
        return passed;
    }

    private static String normalize(String text) { return text.replace("\r\n", "\n").strip(); }

    private static boolean tokens(String expected, Path actual, long deadline) throws IOException {
        try (Reader left = new BufferedReader(new StringReader(expected)); Reader right = Files.newBufferedReader(actual)) {
            while (true) {
                budget(deadline);
                String a = token(left, deadline);
                String b = token(right, deadline);
                if (!java.util.Objects.equals(a, b)) return false;
                if (a == null) return true;
            }
        }
    }

    private static String token(Reader input, long deadline) throws IOException {
        int c;
        do { c = input.read(); } while (c != -1 && Character.isWhitespace(c));
        if (c == -1) return null;
        StringBuilder result = new StringBuilder();
        do {
            result.append((char) c);
            if ((result.length() & 4095) == 0) budget(deadline);
            c = input.read();
        } while (c != -1 && !Character.isWhitespace(c));
        return result.toString();
    }

    private static boolean lines(String expected, Path actual, long deadline) throws IOException {
        Map<String, Integer> counts = new HashMap<>();
        try (BufferedReader reader = new BufferedReader(new StringReader(expected))) {
            String line;
            while ((line = reader.readLine()) != null) {
                budget(deadline);
                counts.merge(line.stripTrailing(), 1, Integer::sum);
            }
        }
        try (BufferedReader reader = Files.newBufferedReader(actual)) {
            String line;
            while ((line = reader.readLine()) != null) {
                budget(deadline);
                String key = line.stripTrailing();
                Integer count = counts.get(key);
                if (count == null) return false;
                if (count == 1) counts.remove(key); else counts.put(key, count - 1);
            }
        }
        return counts.isEmpty();
    }

    private record Triple(long a, long b, long c) { }

    private static boolean triples(String expected, Path actual, long deadline) throws IOException {
        Set<Triple> remaining = new HashSet<>();
        readTriples(new StringReader(expected), triple -> {
            if (!remaining.add(triple)) throw new IllegalStateException("Duplicate triple in standard answer");
        }, deadline);
        try {
            readTriples(Files.newBufferedReader(actual), triple -> {
                // Removing (rather than deduplicating actual output) rejects duplicate user answers.
                if (!remaining.remove(triple)) throw new IllegalArgumentException("Unexpected or duplicate triple");
            }, deadline);
        } catch (IllegalArgumentException | com.fasterxml.jackson.core.JsonProcessingException e) {
            return false;
        }
        return remaining.isEmpty();
    }

    private static void readTriples(Reader source, Consumer<Triple> consume, long deadline) throws IOException {
        try (java.io.PushbackReader reader = new java.io.PushbackReader(new BufferedReader(source), 1)) {
            int first;
            while ((first = reader.read()) != -1 && Character.isWhitespace(first)) budget(deadline);
            if (first == -1) throw new IllegalArgumentException("Expected [] or EMPTY for an empty answer");
            reader.unread(first);
            if (first == '[') {
                try (JsonParser parser = new JsonFactory().createParser(reader)) {
                    if (parser.nextToken() != JsonToken.START_ARRAY) throw new IllegalArgumentException("Expected array");
                    while (parser.nextToken() != JsonToken.END_ARRAY) {
                        budget(deadline);
                        if (parser.currentToken() != JsonToken.START_ARRAY) throw new IllegalArgumentException("Expected triple");
                        long[] values = new long[3];
                        for (int i = 0; i < 3; i++) {
                            if (parser.nextToken() != JsonToken.VALUE_NUMBER_INT) throw new IllegalArgumentException("Expected integer");
                            values[i] = parser.getLongValue();
                        }
                        if (parser.nextToken() != JsonToken.END_ARRAY) throw new IllegalArgumentException("Expected three integers");
                        consume.accept(triple(values));
                    }
                    if (parser.nextToken() != null) throw new IllegalArgumentException("Trailing output");
                }
            } else {
                BufferedReader lines = new BufferedReader(reader);
                String line;
                boolean empty = false;
                int count = 0;
                while ((line = lines.readLine()) != null) {
                    budget(deadline);
                    if (line.isBlank()) continue;
                    if (line.strip().equals("EMPTY") && count == 0 && !empty) { empty = true; continue; }
                    if (empty) throw new IllegalArgumentException("Unexpected output after EMPTY");
                    String[] fields = line.strip().split("\\s+");
                    if (fields.length != 3) throw new IllegalArgumentException("Expected three integers per line");
                    long[] values = new long[]{Long.parseLong(fields[0]), Long.parseLong(fields[1]), Long.parseLong(fields[2])};
                    consume.accept(triple(values));
                    count++;
                }
            }
        }
    }

    private static Triple triple(long[] values) {
        Arrays.sort(values);
        return new Triple(values[0], values[1], values[2]);
    }

    private static void budget(long deadline) {
        if (System.nanoTime() > deadline || Thread.currentThread().isInterrupted()) {
            throw new IllegalStateException("Output checker deadline exceeded");
        }
    }
}
