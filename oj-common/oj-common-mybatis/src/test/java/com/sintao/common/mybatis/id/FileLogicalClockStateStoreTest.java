package com.sintao.common.mybatis.id;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class FileLogicalClockStateStoreTest {

    @TempDir
    Path temporaryDirectory;

    @Test
    void persistsWatermarkAcrossStoreRestart() {
        Path stateFile = temporaryDirectory.resolve("worker-3.properties");
        try (FileLogicalClockStateStore store = new FileLogicalClockStateStore(stateFile)) {
            store.persistHighWatermark(3, 123456L);
        }

        try (FileLogicalClockStateStore restarted = new FileLogicalClockStateStore(stateFile)) {
            assertEquals(123456L, restarted.loadHighWatermark(3).orElseThrow());
        }
    }

    @Test
    void rejectsWorkerIdMismatch() {
        Path stateFile = temporaryDirectory.resolve("worker-mismatch.properties");
        try (FileLogicalClockStateStore store = new FileLogicalClockStateStore(stateFile)) {
            store.persistHighWatermark(3, 123456L);
            assertThrows(IllegalStateException.class, () -> store.loadHighWatermark(4));
        }
    }

    @Test
    void preventsTwoProcessesFromSharingOneStateFile() {
        Path stateFile = temporaryDirectory.resolve("locked.properties");
        try (FileLogicalClockStateStore ignored = new FileLogicalClockStateStore(stateFile)) {
            assertThrows(IllegalStateException.class, () -> new FileLogicalClockStateStore(stateFile));
        }
    }
}
