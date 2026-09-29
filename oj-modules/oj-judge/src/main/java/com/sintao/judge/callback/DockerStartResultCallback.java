package com.sintao.judge.callback;


import com.github.dockerjava.api.model.Frame;
import com.github.dockerjava.api.model.StreamType;
import com.github.dockerjava.core.command.ExecStartResultCallback;

import java.nio.charset.StandardCharsets;

public class DockerStartResultCallback extends ExecStartResultCallback {

    private static final int MAX_OUTPUT_CHARS = 1_048_576;
    private final StringBuilder stderr = new StringBuilder();
    private final StringBuilder stdout = new StringBuilder();
    private boolean outputTruncated;

    public String getErrorMessage() {
        return stderr.toString();
    }

    public String getMessage() {
        return stdout.toString();
    }

    public boolean isOutputTruncated() {
        return outputTruncated;
    }

    @Override
    public void onNext(Frame frame) {
        StreamType streamType = frame.getStreamType();
        String chunk = new String(frame.getPayload(), StandardCharsets.UTF_8);
        if (StreamType.STDERR.equals(streamType)) {
            appendBounded(stderr, chunk);
        } else if (StreamType.STDOUT.equals(streamType)) {
            appendBounded(stdout, chunk);
        }
        super.onNext(frame);
    }

    private void appendBounded(StringBuilder output, String chunk) {
        int remaining = MAX_OUTPUT_CHARS - output.length();
        if (remaining <= 0) {
            outputTruncated = true;
            return;
        }
        if (chunk.length() > remaining) {
            output.append(chunk, 0, remaining);
            outputTruncated = true;
        } else {
            output.append(chunk);
        }
    }
}

