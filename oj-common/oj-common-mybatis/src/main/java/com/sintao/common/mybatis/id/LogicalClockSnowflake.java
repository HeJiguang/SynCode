package com.sintao.common.mybatis.id;

import java.util.OptionalLong;
import java.util.function.LongSupplier;

public final class LogicalClockSnowflake implements AutoCloseable {

    // Keep the MyBatis-Plus epoch so migrated IDs remain in the existing numeric timeline.
    public static final long DEFAULT_EPOCH_MILLIS = 1288834974657L;
    public static final long MAX_WORKER_ID = 1023L;

    private static final int WORKER_ID_BITS = 10;
    private static final int SEQUENCE_BITS = 12;
    private static final int TIMESTAMP_SHIFT = WORKER_ID_BITS + SEQUENCE_BITS;
    private static final long SEQUENCE_MASK = (1L << SEQUENCE_BITS) - 1;
    private static final long MAX_TIMESTAMP_OFFSET = (1L << 41) - 1;

    private final long workerId;
    private final long epochMillis;
    private final long reservationMillis;
    private final LongSupplier timeSource;
    private final LogicalClockStateStore stateStore;

    private long lastTimestamp;
    private long sequence = -1L;
    private long reservedThrough;

    public LogicalClockSnowflake(long workerId,
                                 long epochMillis,
                                 long reservationMillis,
                                 LongSupplier timeSource,
                                 LogicalClockStateStore stateStore) {
        if (workerId < 0 || workerId > MAX_WORKER_ID) {
            throw new IllegalArgumentException("workerId must be between 0 and " + MAX_WORKER_ID);
        }
        if (reservationMillis <= 0) {
            throw new IllegalArgumentException("reservationMillis must be positive");
        }
        this.workerId = workerId;
        this.epochMillis = epochMillis;
        this.reservationMillis = reservationMillis;
        this.timeSource = timeSource;
        this.stateStore = stateStore;

        long physicalNow = timeSource.getAsLong();
        OptionalLong persistedWatermark = stateStore.loadHighWatermark(workerId);
        this.lastTimestamp = persistedWatermark.isPresent()
                ? Math.max(physicalNow, incrementExact(persistedWatermark.getAsLong()))
                : physicalNow;
        validateTimestamp(lastTimestamp);
        reserveThrough(lastTimestamp);
    }

    public synchronized long nextId() {
        long logicalTimestamp = Math.max(timeSource.getAsLong(), lastTimestamp);
        if (logicalTimestamp == lastTimestamp) {
            if (sequence >= SEQUENCE_MASK) {
                logicalTimestamp = incrementExact(lastTimestamp);
                sequence = 0L;
            } else {
                sequence++;
            }
        } else {
            sequence = 0L;
        }

        validateTimestamp(logicalTimestamp);
        reserveThrough(logicalTimestamp);
        lastTimestamp = logicalTimestamp;
        return ((logicalTimestamp - epochMillis) << TIMESTAMP_SHIFT)
                | (workerId << SEQUENCE_BITS)
                | sequence;
    }

    public static long extractTimestamp(long id, long epochMillis) {
        return (id >>> TIMESTAMP_SHIFT) + epochMillis;
    }

    public static long extractWorkerId(long id) {
        return (id >>> SEQUENCE_BITS) & MAX_WORKER_ID;
    }

    @Override
    public void close() {
        stateStore.close();
    }

    private void reserveThrough(long timestamp) {
        if (timestamp <= reservedThrough) {
            return;
        }
        long newHighWatermark = addExact(timestamp, reservationMillis);
        validateTimestamp(newHighWatermark);
        stateStore.persistHighWatermark(workerId, newHighWatermark);
        reservedThrough = newHighWatermark;
    }

    private void validateTimestamp(long timestamp) {
        if (timestamp < epochMillis) {
            throw new IllegalStateException("Logical timestamp is before the configured epoch");
        }
        if (timestamp - epochMillis > MAX_TIMESTAMP_OFFSET) {
            throw new IllegalStateException("Logical timestamp exceeds the 41-bit Snowflake range");
        }
    }

    private static long incrementExact(long value) {
        return addExact(value, 1L);
    }

    private static long addExact(long left, long right) {
        try {
            return Math.addExact(left, right);
        } catch (ArithmeticException e) {
            throw new IllegalStateException("Logical timestamp overflow", e);
        }
    }
}
