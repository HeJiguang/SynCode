package com.sintao.judge.scheduler;

import com.sintao.common.core.enums.JudgeTaskType;
import com.sintao.judge.config.JudgeExecutionCapacity;
import com.sintao.judge.config.JudgeSchedulingProperties;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class LocalJudgeSchedulerTest {

    @Test
    void runsTasksUpToLocalCapacityConcurrently() throws Exception {
        LocalJudgeScheduler scheduler = new LocalJudgeScheduler(
                new JudgeExecutionCapacity("pool", 2, 0)
        );
        CountDownLatch started = new CountDownLatch(2);
        CountDownLatch release = new CountDownLatch(1);
        try {
            CompletableFuture<Void> first = scheduler.submit("req-1", () -> await(started, release));
            CompletableFuture<Void> second = scheduler.submit("req-2", () -> await(started, release));

            assertTrue(started.await(2, TimeUnit.SECONDS));
            assertEquals(2, scheduler.snapshot().activeTasks());
            assertEquals(0, scheduler.snapshot().queuedTasks());
            assertEquals(2, scheduler.snapshot().availablePermits());

            release.countDown();
            CompletableFuture.allOf(first, second).get(2, TimeUnit.SECONDS);
            assertEquals(2, scheduler.snapshot().completedTasks());
        } finally {
            release.countDown();
            scheduler.close();
        }
    }

    @Test
    void rejectsWorkBeyondRunningAndQueuedAdmissionCapacity() throws Exception {
        LocalJudgeScheduler scheduler = new LocalJudgeScheduler(
                new JudgeExecutionCapacity("pool", 1, 0)
        );
        CountDownLatch started = new CountDownLatch(1);
        CountDownLatch release = new CountDownLatch(1);
        try {
            CompletableFuture<Void> first = scheduler.submit("req-1", () -> await(started, release));
            assertTrue(started.await(2, TimeUnit.SECONDS));

            CompletableFuture<Void> queued = scheduler.submit("req-2", () -> { });
            CompletableFuture<Void> rejected = scheduler.submit("req-3", () -> { });
            ExecutionException exception = assertThrows(
                    ExecutionException.class,
                    () -> rejected.get(2, TimeUnit.SECONDS)
            );
            assertInstanceOf(RejectedExecutionException.class, exception.getCause());

            release.countDown();
            CompletableFuture.allOf(first, queued).get(2, TimeUnit.SECONDS);
        } finally {
            release.countDown();
            scheduler.close();
        }
    }

    @Test
    void prioritizesRealtimeButGuaranteesBatchProgress() throws Exception {
        LocalJudgeScheduler scheduler = new LocalJudgeScheduler(
                new JudgeExecutionCapacity("pool", 1, 0),
                new JudgeSchedulingProperties(2, 4)
        );
        CountDownLatch blockerStarted = new CountDownLatch(1);
        CountDownLatch releaseBlocker = new CountDownLatch(1);
        List<String> order = new CopyOnWriteArrayList<>();
        try {
            CompletableFuture<Void> blocker = scheduler.submit(
                    JudgeTaskType.BATCH,
                    "blocker",
                    () -> await(blockerStarted, releaseBlocker)
            );
            assertTrue(blockerStarted.await(2, TimeUnit.SECONDS));

            CompletableFuture<Void> realtime1 = scheduler.submit(JudgeTaskType.REALTIME, "r1", () -> order.add("r1"));
            CompletableFuture<Void> realtime2 = scheduler.submit(JudgeTaskType.REALTIME, "r2", () -> order.add("r2"));
            CompletableFuture<Void> realtime3 = scheduler.submit(JudgeTaskType.REALTIME, "r3", () -> order.add("r3"));
            CompletableFuture<Void> batch = scheduler.submit(JudgeTaskType.BATCH, "b1", () -> order.add("b1"));

            releaseBlocker.countDown();
            CompletableFuture.allOf(blocker, realtime1, realtime2, realtime3, batch).get(2, TimeUnit.SECONDS);

            assertEquals(List.of("r1", "r2", "b1", "r3"), order);
        } finally {
            releaseBlocker.countDown();
            scheduler.close();
        }
    }

    private void await(CountDownLatch started, CountDownLatch release) {
        started.countDown();
        try {
            release.await();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Interrupted test task", e);
        }
    }
}
