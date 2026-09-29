package com.sintao.judge.callback;

import com.github.dockerjava.api.model.Frame;
import com.github.dockerjava.api.model.StreamType;
import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class DockerStartResultCallbackTest {

    @Test
    void stdoutFramesShouldBeAccumulated() {
        DockerStartResultCallback callback = new DockerStartResultCallback();

        callback.onNext(frame(StreamType.STDOUT, "hello "));
        callback.onNext(frame(StreamType.STDOUT, "world"));

        assertEquals("hello world", callback.getMessage());
    }

    @Test
    void stderrAndStdoutShouldBeCapturedSeparately() {
        DockerStartResultCallback callback = new DockerStartResultCallback();

        callback.onNext(frame(StreamType.STDERR, "failure"));
        callback.onNext(frame(StreamType.STDOUT, "partial output"));

        assertEquals("failure", callback.getErrorMessage());
        assertEquals("partial output", callback.getMessage());
    }

    @Test
    void outputFloodShouldBeTruncatedBeforeItExhaustsJudgeMemory() {
        DockerStartResultCallback callback = new DockerStartResultCallback();
        String chunk = "x".repeat(600_000);

        callback.onNext(frame(StreamType.STDOUT, chunk));
        callback.onNext(frame(StreamType.STDOUT, chunk));

        assertEquals(1_048_576, callback.getMessage().length());
        assertTrue(callback.isOutputTruncated());
    }

    private Frame frame(StreamType type, String payload) {
        return new Frame(type, payload.getBytes(StandardCharsets.UTF_8));
    }
}
