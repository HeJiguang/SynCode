package com.sintao.common.mybatis.id;

import org.junit.jupiter.api.Test;

import java.util.OptionalLong;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class LogicalClockSnowflakeTest {

    private static final long NOW = LogicalClockSnowflake.DEFAULT_EPOCH_MILLIS + 1_000_000L;

    @Test
    void keepsIdsIncreasingWhenPhysicalClockMovesBackwards() {
        AtomicLong clock = new AtomicLong(NOW);
        LogicalClockSnowflake generator = generator(7, clock, new InMemoryStateStore());

        long first = generator.nextId();
        clock.addAndGet(-60_000L);
        long second = generator.nextId();

        assertTrue(second > first);
        assertEquals(
                LogicalClockSnowflake.extractTimestamp(first, LogicalClockSnowflake.DEFAULT_EPOCH_MILLIS),
                LogicalClockSnowflake.extractTimestamp(second, LogicalClockSnowflake.DEFAULT_EPOCH_MILLIS));
    }

    @Test
    void advancesLogicalTimestampWhenSequenceIsExhausted() {
        AtomicLong clock = new AtomicLong(NOW);
        LogicalClockSnowflake generator = generator(8, clock, new InMemoryStateStore());

        long first = generator.nextId();
        long latest = first;
        for (int i = 0; i < 4096; i++) {
            latest = generator.nextId();
        }

        assertTrue(latest > first);
        assertEquals(
                LogicalClockSnowflake.extractTimestamp(first, LogicalClockSnowflake.DEFAULT_EPOCH_MILLIS) + 1,
                LogicalClockSnowflake.extractTimestamp(latest, LogicalClockSnowflake.DEFAULT_EPOCH_MILLIS));
    }

    @Test
    void startsAfterPersistedReservationOnRestart() {
        AtomicLong firstClock = new AtomicLong(NOW);
        InMemoryStateStore stateStore = new InMemoryStateStore();
        LogicalClockSnowflake firstGenerator = generator(9, firstClock, stateStore);
        long beforeRestart = firstGenerator.nextId();

        AtomicLong rolledBackClock = new AtomicLong(NOW - 120_000L);
        LogicalClockSnowflake restartedGenerator = generator(9, rolledBackClock, stateStore);
        long afterRestart = restartedGenerator.nextId();

        assertTrue(afterRestart > beforeRestart);
        assertTrue(LogicalClockSnowflake.extractTimestamp(
                afterRestart, LogicalClockSnowflake.DEFAULT_EPOCH_MILLIS) > NOW);
    }

    @Test
    void workerBitsKeepNodesDistinct() {
        AtomicLong clock = new AtomicLong(NOW);
        long first = generator(10, clock, new InMemoryStateStore()).nextId();
        long second = generator(11, clock, new InMemoryStateStore()).nextId();

        assertNotEquals(first, second);
        assertEquals(10, LogicalClockSnowflake.extractWorkerId(first));
        assertEquals(11, LogicalClockSnowflake.extractWorkerId(second));
    }

    @Test
    void generatesUniqueIdsAcrossConcurrentCallers() throws Exception {
        int threadCount = 8;
        int idsPerThread = 5_000;
        LogicalClockSnowflake generator = generator(
                12,
                new AtomicLong(NOW),
                new InMemoryStateStore());
        Set<Long> ids = ConcurrentHashMap.newKeySet();
        ExecutorService executor = Executors.newFixedThreadPool(threadCount);

        for (int thread = 0; thread < threadCount; thread++) {
            executor.submit(() -> {
                for (int i = 0; i < idsPerThread; i++) {
                    ids.add(generator.nextId());
                }
            });
        }
        executor.shutdown();

        assertTrue(executor.awaitTermination(10, TimeUnit.SECONDS));
        assertEquals(threadCount * idsPerThread, ids.size());
    }

    private LogicalClockSnowflake generator(long workerId,
                                             AtomicLong clock,
                                             LogicalClockStateStore stateStore) {
        return new LogicalClockSnowflake(
                workerId,
                LogicalClockSnowflake.DEFAULT_EPOCH_MILLIS,
                10_000L,
                clock::get,
                stateStore);
    }

    private static final class InMemoryStateStore implements LogicalClockStateStore {

        private Long workerId;
        private Long highWatermark;

        @Override
        public OptionalLong loadHighWatermark(long requestedWorkerId) {
            if (highWatermark == null) {
                return OptionalLong.empty();
            }
            if (!workerId.equals(requestedWorkerId)) {
                throw new IllegalStateException("workerId mismatch");
            }
            return OptionalLong.of(highWatermark);
        }

        @Override
        public void persistHighWatermark(long requestedWorkerId, long newHighWatermark) {
            workerId = requestedWorkerId;
            highWatermark = newHighWatermark;
        }
    }
}
