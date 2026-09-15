package com.sintao.judge.callback;

import com.github.dockerjava.api.model.Frame;
import com.github.dockerjava.api.model.StreamType;
import com.sintao.common.core.enums.CodeRunStatus;
import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;

import static org.junit.jupiter.api.Assertions.assertEquals;

class DockerStartResultCallbackTest {

    @Test
    void stdoutFramesShouldBeAccumulated() {
        DockerStartResultCallback callback = new DockerStartResultCallback();

        callback.onNext(frame(StreamType.STDOUT, "hello "));
        callback.onNext(frame(StreamType.STDOUT, "world"));

        assertEquals("hello world", callback.getMessage());
        assertEquals(CodeRunStatus.SUCCEED, callback.getCodeRunStatus());
    }

    @Test
    void stderrShouldKeepExecutionFailedAfterLaterStdout() {
        DockerStartResultCallback callback = new DockerStartResultCallback();

        callback.onNext(frame(StreamType.STDERR, "failure"));
        callback.onNext(frame(StreamType.STDOUT, "partial output"));

        assertEquals("failure", callback.getErrorMessage());
        assertEquals(CodeRunStatus.FAILED, callback.getCodeRunStatus());
    }

    private Frame frame(StreamType type, String payload) {
        return new Frame(type, payload.getBytes(StandardCharsets.UTF_8));
    }
}
