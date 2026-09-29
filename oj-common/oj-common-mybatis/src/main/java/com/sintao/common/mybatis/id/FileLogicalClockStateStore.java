package com.sintao.common.mybatis.id;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.channels.OverlappingFileLockException;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.util.OptionalLong;
import java.util.Properties;

public final class FileLogicalClockStateStore implements LogicalClockStateStore {

    private static final String FORMAT_VERSION = "1";

    private final Path stateFile;
    private final FileChannel lockChannel;
    private final FileLock lock;

    public FileLogicalClockStateStore(Path stateFile) {
        try {
            this.stateFile = stateFile.toAbsolutePath().normalize();
            Path parent = this.stateFile.getParent();
            if (parent == null) {
                throw new IllegalArgumentException("State file must have a parent directory");
            }
            Files.createDirectories(parent);
            Path lockFile = parent.resolve(this.stateFile.getFileName() + ".lock");
            this.lockChannel = FileChannel.open(lockFile,
                    StandardOpenOption.CREATE,
                    StandardOpenOption.WRITE);
            this.lock = tryAcquireLock(lockChannel);
            if (this.lock == null) {
                lockChannel.close();
                throw new IllegalStateException("ID state file is already in use: " + this.stateFile);
            }
        } catch (IOException e) {
            throw new IllegalStateException("Cannot initialize ID state file: " + stateFile, e);
        }
    }

    @Override
    public OptionalLong loadHighWatermark(long workerId) {
        if (!Files.exists(stateFile)) {
            return OptionalLong.empty();
        }

        Properties properties = new Properties();
        try (InputStream input = Files.newInputStream(stateFile)) {
            properties.load(input);
        } catch (IOException e) {
            throw new IllegalStateException("Cannot read ID state file: " + stateFile, e);
        }

        String version = properties.getProperty("version");
        if (!FORMAT_VERSION.equals(version)) {
            throw new IllegalStateException("Unsupported ID state file version: " + version);
        }

        long storedWorkerId = parseLong(properties, "workerId");
        if (storedWorkerId != workerId) {
            throw new IllegalStateException(
                    "ID state workerId mismatch: expected " + workerId + " but found " + storedWorkerId);
        }
        return OptionalLong.of(parseLong(properties, "highWatermark"));
    }

    @Override
    public void persistHighWatermark(long workerId, long highWatermark) {
        Properties properties = new Properties();
        properties.setProperty("version", FORMAT_VERSION);
        properties.setProperty("workerId", Long.toString(workerId));
        properties.setProperty("highWatermark", Long.toString(highWatermark));

        Path parent = stateFile.getParent();
        Path temporaryFile;
        try {
            temporaryFile = Files.createTempFile(parent, stateFile.getFileName().toString(), ".tmp");
            try (OutputStream output = Files.newOutputStream(temporaryFile, StandardOpenOption.TRUNCATE_EXISTING)) {
                properties.store(output, "SynCode logical-clock Snowflake state");
            }
            try (FileChannel channel = FileChannel.open(temporaryFile, StandardOpenOption.WRITE)) {
                channel.force(true);
            }
            moveAtomically(temporaryFile, stateFile);
        } catch (IOException e) {
            throw new IllegalStateException("Cannot persist ID high watermark: " + stateFile, e);
        }
    }

    @Override
    public void close() {
        try {
            lock.release();
        } catch (IOException ignored) {
            // Closing the channel below also releases the process lock.
        }
        try {
            lockChannel.close();
        } catch (IOException ignored) {
            // Nothing useful can be done during application shutdown.
        }
    }

    private static FileLock tryAcquireLock(FileChannel channel) throws IOException {
        try {
            return channel.tryLock();
        } catch (OverlappingFileLockException e) {
            return null;
        }
    }

    private static long parseLong(Properties properties, String key) {
        String value = properties.getProperty(key);
        if (value == null || value.isBlank()) {
            throw new IllegalStateException("Missing " + key + " in ID state file");
        }
        try {
            return Long.parseLong(value);
        } catch (NumberFormatException e) {
            throw new IllegalStateException("Invalid " + key + " in ID state file: " + value, e);
        }
    }

    private static void moveAtomically(Path source, Path target) throws IOException {
        try {
            Files.move(source, target,
                    StandardCopyOption.ATOMIC_MOVE,
                    StandardCopyOption.REPLACE_EXISTING);
        } catch (AtomicMoveNotSupportedException e) {
            Files.move(source, target, StandardCopyOption.REPLACE_EXISTING);
        }
    }
}
