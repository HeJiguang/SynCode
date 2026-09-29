package com.sintao.judge.scheduler;

import com.sintao.common.core.enums.JudgeTaskType;
import com.sintao.judge.config.JudgeExecutionCapacity;
import com.sintao.judge.config.JudgeSchedulingProperties;
import jakarta.annotation.PreDestroy;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.Semaphore;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.locks.Condition;
import java.util.concurrent.locks.ReentrantLock;

@Component
@Slf4j
public class LocalJudgeScheduler implements AutoCloseable {

    private static final long SHUTDOWN_WAIT_SECONDS = 30;

    private final int capacity;
    private final int maxInFlight;
    private final int realtimeBurst;
    private final Semaphore admissionPermits;
    private final ReentrantLock queueLock = new ReentrantLock();
    private final Condition workAvailable = queueLock.newCondition();
    private final ArrayDeque<ScheduledJudgeTask> realtimeQueue = new ArrayDeque<>();
    private final ArrayDeque<ScheduledJudgeTask> batchQueue = new ArrayDeque<>();
    private final List<Thread> workers = new ArrayList<>();
    private final AtomicInteger activeTasks = new AtomicInteger();
    private final AtomicLong completedTasks = new AtomicLong();

    private volatile boolean accepting = true;
    private volatile boolean forceStop;
    private int consecutiveRealtime;

    @Autowired
    public LocalJudgeScheduler(JudgeExecutionCapacity executionCapacity,
                               JudgeSchedulingProperties schedulingProperties) {
        this.capacity = executionCapacity.value();
        this.realtimeBurst = schedulingProperties.realtimeBurst();
        this.maxInFlight = capacity + schedulingProperties.queueCapacity(capacity);
        this.admissionPermits = new Semaphore(maxInFlight);
        startWorkers();
    }

    LocalJudgeScheduler(JudgeExecutionCapacity executionCapacity) {
        this(executionCapacity, new JudgeSchedulingProperties(4, 1));
    }

    public CompletableFuture<Void> submit(String requestId, Runnable task) {
        return submit(JudgeTaskType.REALTIME, requestId, task);
    }

    public CompletableFuture<Void> submit(JudgeTaskType taskType, String requestId, Runnable task) {
        Objects.requireNonNull(task, "task");
        JudgeTaskType resolvedType = taskType == null ? JudgeTaskType.REALTIME : taskType;
        CompletableFuture<Void> completion = new CompletableFuture<>();
        if (!admissionPermits.tryAcquire()) {
            completion.completeExceptionally(new RejectedExecutionException(
                    "Local judge scheduler is full, requestId=" + requestId
            ));
            return completion;
        }

        queueLock.lock();
        try {
            if (!accepting) {
                admissionPermits.release();
                completion.completeExceptionally(new RejectedExecutionException("Local judge scheduler is stopping"));
                return completion;
            }
            ScheduledJudgeTask scheduledTask = new ScheduledJudgeTask(requestId, task, completion);
            if (resolvedType == JudgeTaskType.BATCH) {
                batchQueue.addLast(scheduledTask);
            } else {
                realtimeQueue.addLast(scheduledTask);
            }
            workAvailable.signal();
            return completion;
        } finally {
            queueLock.unlock();
        }
    }

    public SchedulerSnapshot snapshot() {
        queueLock.lock();
        try {
            return new SchedulerSnapshot(
                    capacity,
                    maxInFlight,
                    activeTasks.get(),
                    realtimeQueue.size() + batchQueue.size(),
                    realtimeQueue.size(),
                    batchQueue.size(),
                    admissionPermits.availablePermits(),
                    completedTasks.get()
            );
        } finally {
            queueLock.unlock();
        }
    }

    private void startWorkers() {
        for (int index = 1; index <= capacity; index++) {
            Thread worker = new Thread(this::workerLoop, "local-judge-worker-" + index);
            worker.setDaemon(false);
            workers.add(worker);
            worker.start();
        }
    }

    private void workerLoop() {
        while (true) {
            ScheduledJudgeTask scheduledTask;
            try {
                scheduledTask = takeNext();
            } catch (InterruptedException e) {
                if (forceStop) {
                    Thread.currentThread().interrupt();
                    return;
                }
                continue;
            }
            if (scheduledTask == null) {
                return;
            }
            execute(scheduledTask);
        }
    }

    private ScheduledJudgeTask takeNext() throws InterruptedException {
        queueLock.lockInterruptibly();
        try {
            while (!forceStop && realtimeQueue.isEmpty() && batchQueue.isEmpty()) {
                if (!accepting) {
                    return null;
                }
                workAvailable.await();
            }
            if (forceStop) {
                return null;
            }
            if (!realtimeQueue.isEmpty()
                    && (batchQueue.isEmpty() || consecutiveRealtime < realtimeBurst)) {
                consecutiveRealtime = Math.min(realtimeBurst, consecutiveRealtime + 1);
                return realtimeQueue.removeFirst();
            }
            if (!batchQueue.isEmpty()) {
                consecutiveRealtime = 0;
                return batchQueue.removeFirst();
            }
            consecutiveRealtime = Math.min(realtimeBurst, consecutiveRealtime + 1);
            return realtimeQueue.removeFirst();
        } finally {
            queueLock.unlock();
        }
    }

    private void execute(ScheduledJudgeTask scheduledTask) {
        Throwable failure = null;
        activeTasks.incrementAndGet();
        try {
            scheduledTask.task().run();
        } catch (Throwable throwable) {
            failure = throwable;
        } finally {
            activeTasks.decrementAndGet();
            completedTasks.incrementAndGet();
            admissionPermits.release();
        }

        if (failure == null) {
            scheduledTask.completion().complete(null);
            return;
        }
        log.error("Local judge task failed, requestId={}", scheduledTask.requestId(), failure);
        scheduledTask.completion().completeExceptionally(failure);
    }

    @Override
    @PreDestroy
    public void close() {
        accepting = false;
        signalAllWorkers();
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(SHUTDOWN_WAIT_SECONDS);
        for (Thread worker : workers) {
            long remaining = deadline - System.nanoTime();
            if (remaining <= 0) {
                break;
            }
            try {
                worker.join(Math.max(1, TimeUnit.NANOSECONDS.toMillis(remaining)));
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            }
        }
        if (workers.stream().anyMatch(Thread::isAlive)) {
            forceStop = true;
            workers.forEach(Thread::interrupt);
            rejectQueuedTasks();
            signalAllWorkers();
        }
    }

    private void signalAllWorkers() {
        queueLock.lock();
        try {
            workAvailable.signalAll();
        } finally {
            queueLock.unlock();
        }
    }

    private void rejectQueuedTasks() {
        queueLock.lock();
        try {
            RejectedExecutionException failure = new RejectedExecutionException("Local judge scheduler stopped");
            rejectQueue(realtimeQueue, failure);
            rejectQueue(batchQueue, failure);
        } finally {
            queueLock.unlock();
        }
    }

    private void rejectQueue(ArrayDeque<ScheduledJudgeTask> queue, RejectedExecutionException failure) {
        ScheduledJudgeTask task;
        while ((task = queue.pollFirst()) != null) {
            admissionPermits.release();
            task.completion().completeExceptionally(failure);
        }
    }

    public record SchedulerSnapshot(int capacity,
                                    int maxInFlight,
                                    int activeTasks,
                                    int queuedTasks,
                                    int realtimeQueuedTasks,
                                    int batchQueuedTasks,
                                    int availablePermits,
                                    long completedTasks) {
    }

    private record ScheduledJudgeTask(String requestId,
                                      Runnable task,
                                      CompletableFuture<Void> completion) {
    }
}
