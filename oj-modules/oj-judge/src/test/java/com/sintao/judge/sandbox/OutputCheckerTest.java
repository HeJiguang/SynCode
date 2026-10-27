package com.sintao.judge.sandbox;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.concurrent.TimeUnit;
import static org.junit.jupiter.api.Assertions.*;

class OutputCheckerTest {
    @TempDir Path directory;

    private boolean check(String checker, String expected, String actual) throws Exception {
        Path file = directory.resolve("output.txt");
        Files.writeString(file, actual);
        return OutputChecker.check(checker, expected, file, System.nanoTime() + TimeUnit.SECONDS.toNanos(10));
    }

    @Test void triplesAcceptDifferentOrderAndDifferentSupportedFormats() throws Exception {
        assertTrue(check("unorderedTriples", "-1 -1 2\n-1 0 1", "[[1,-1,0],[2,-1,-1]]"));
        assertTrue(check("unorderedTriples", "[]", "EMPTY\n"));
        assertTrue(check("unorderedTriples", "EMPTY", "[]"));
    }

    @Test void triplesRejectDuplicatesMissingExtraMalformedAndTrailingContent() throws Exception {
        String expected = "[[-1,-1,2],[-1,0,1]]";
        for (String actual : new String[]{"[[-1,-1,2],[-1,-1,2],[-1,0,1]]", "[[-1,-1,2]]",
                "[[-1,-1,2],[-1,0,1],[0,0,0]]", "[[-1,-1,2,0],[-1,0,1]]",
                "[[-1,-1,2],[-1,0,1]] garbage", "", "EMPTY\n-1 -1 2", "[[1.0,-1,0]]"}) {
            assertFalse(check("unorderedTriples", expected, actual), actual);
        }
    }

    @Test void unorderedLinesPreserveMultiplicity() throws Exception {
        assertTrue(check("unorderedLines", "a\na\nb", "b\na\na"));
        assertFalse(check("unorderedLines", "a\na\nb", "b\na"));
        assertFalse(check("unorderedLines", "a\na\nb", "b\na\nb"));
    }

    @Test void defaultKeepsInternalOrderWhileTokensIgnoreWhitespace() throws Exception {
        assertTrue(check("text", "1\n2", " 1\r\n2\n"));
        assertFalse(check("text", "1 2", "2 1"));
        assertFalse(check("exact", "1", "1\n"));
        assertTrue(check("tokens", "1 2\n3", "1\n2   3\n"));
        assertFalse(check("tokens", "1 2", "1 2 3"));
        assertThrows(IllegalArgumentException.class, () -> OutputChecker.resolve("{\"checker\":\"unknown\"}"));
    }

    @Test void mismatchesPastThePreviewAreStillChecked() throws Exception {
        assertFalse(check("text", "a".repeat(10000) + "x", "a".repeat(10000) + "y"));
    }
}
