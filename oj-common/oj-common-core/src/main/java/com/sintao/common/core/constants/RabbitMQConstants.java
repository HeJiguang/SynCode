package com.sintao.common.core.constants;

public class RabbitMQConstants {

    public static final String OJ_JUDGE_EXCHANGE = "oj.judge.exchange";

    public static final String OJ_JUDGE_DLX_EXCHANGE = "oj.judge.dlx.exchange";

    public static final String OJ_WORK_QUEUE = "oj-work-queue";

    public static final String OJ_BATCH_QUEUE = "oj.judge.batch.queue";

    public static final String OJ_RETRY_QUEUE = "oj.judge.retry.queue";

    public static final String OJ_BATCH_RETRY_QUEUE = "oj.judge.batch.retry.queue";

    public static final String OJ_DEAD_QUEUE = "oj.judge.dead.queue";

    public static final String JUDGE_SUBMIT_KEY = "judge.submit";

    public static final String JUDGE_BATCH_KEY = "judge.batch";

    public static final String JUDGE_RETRY_KEY = "judge.retry";

    public static final String JUDGE_BATCH_RETRY_KEY = "judge.batch.retry";

    public static final String JUDGE_DEAD_KEY = "judge.dead";

    private RabbitMQConstants() {
    }
}

