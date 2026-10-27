package com.sintao.judge.sandbox;

import com.alibaba.fastjson2.JSONObject;
import com.sintao.api.domain.UserExeResult;
import com.sintao.api.domain.dto.JudgeSubmitDTO;
import com.sintao.common.core.enums.CodeRunStatus;
import com.sintao.common.redis.service.JudgeCaseStore;
import com.sintao.judge.config.GoJudgeProperties;
import com.sintao.judge.domain.SandBoxExecuteResult;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Semaphore;
import java.util.concurrent.TimeUnit;

/** One compilation per submission, one fresh user process and reset environment per case. */
@Service
@ConditionalOnProperty(name = "sandbox.execution.mode", havingValue = "go-judge")
public class GoJudgeSandboxService {
    private final GoJudgeClient client;
    private final JudgeCaseStore cases;
    private final GoJudgeProperties config;
    private final Semaphore slots;
    // Large unordered standard answers must not allocate several hash tables concurrently.
    private final Semaphore checkerSlot = new Semaphore(1, true);

    public GoJudgeSandboxService(GoJudgeClient client, JudgeCaseStore cases, GoJudgeProperties config) {
        config.validate();
        this.client = client;
        this.cases = cases;
        this.config = config;
        this.slots = new Semaphore(config.getParallelism(), true);
    }

    public SandBoxExecuteResult execute(JudgeSubmitDTO submission, boolean sampleRun) {
        long timeMs = requireLimit(submission.getTimeLimit(), config.getMaxTimeMs(), "timeLimit (ms)");
        long memoryKiB = requireLimit(submission.getSpaceLimit(), config.getMaxMemoryBytes() / 1024, "spaceLimit (KiB)");
        int count = caseCount(submission);
        String checker = OutputChecker.resolve(submission.getGradingConfigJson());
        GoJudgeLanguage language = GoJudgeLanguage.of(submission.getProgramType(), memoryKiB * 1024);
        long budgetMs = Math.min(config.getMaxSubmissionTimeMs(),
                config.getCompileTimeMs() * config.getClockMultiplier()
                        + count * (timeMs * config.getClockMultiplier() + config.getCheckerTimeMs()));
        long deadline = System.nanoTime() + TimeUnit.MILLISECONDS.toNanos(budgetMs);
        boolean acquired = false;
        JSONObject compiled = null;
        try {
            acquired = slots.tryAcquire(budgetMs, TimeUnit.MILLISECONDS);
            if (!acquired) throw new IllegalStateException("No sandbox execution slot available");
            Map<String, Object> compile = command(language.compile(), "", config.getCompileTimeMs(),
                    config.getCompileMemoryBytes(), Math.min(remaining(deadline),
                            config.getCompileTimeMs() * config.getClockMultiplier()), 65536);
            compile.put("copyIn", Map.of(language.source(), Map.of("content", submission.getUserCode())));
            compile.put("copyOutCached", List.of(language.artifact() + "?"));
            compile.put("copyOutMax", config.getArtifactLimitBytes());
            compiled = client.run(compile, nanosToMillis((long) compile.get("clockLimit")));
            checkInfrastructure(compiled);
            if (!"Accepted".equals(compiled.getString("status"))) {
                return SandBoxExecuteResult.fail(CodeRunStatus.COMPILE_FAILED,
                        "编译失败（" + compiled.getString("status") + "）：" + diagnostic(compiled));
            }
            JSONObject fileIds = compiled.getJSONObject("fileIds");
            String artifactId = fileIds == null ? null : fileIds.getString(language.artifact());
            if (artifactId == null) throw new IllegalStateException("Compiler produced no cached artifact");
            return runCases(submission, sampleRun, language, artifactId, count, timeMs, memoryKiB * 1024,
                    checker, deadline);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Interrupted while waiting for sandbox", e);
        } finally {
            if (compiled != null) client.deleteResultFiles(compiled);
            if (acquired) slots.release();
        }
    }

    private SandBoxExecuteResult runCases(JudgeSubmitDTO submission, boolean sampleRun, GoJudgeLanguage language,
                                          String artifactId, int count, long timeMs, long memoryBytes,
                                          String checker, long deadline) {
        List<UserExeResult> details = new ArrayList<>();
        SandBoxExecuteResult result = SandBoxExecuteResult.success(CodeRunStatus.SUCCEED, List.of(), 0L, 0L);
        result.setAllCasesPassed(true);
        result.setCaseResults(details);
        result.setExecutedCaseCount(0);
        long totalOutput = 0;
        for (int i = 0; i < count; i++) {
            if (remaining(deadline) <= 0) {
                result.setRunStatus(CodeRunStatus.OUT_OF_TIME);
                result.setExeMessage("整次提交执行预算耗尽");
                result.setAllCasesPassed(false);
                break;
            }
            JudgeCaseStore.TestCase test = readCase(submission, i);
            long clockMs = Math.min(remaining(deadline), timeMs * config.getClockMultiplier());
            Map<String, Object> command = command(language.run(), test.input(), timeMs, memoryBytes,
                    clockMs, Math.min(config.getOutputLimitBytes(), config.getTotalOutputLimitBytes() - totalOutput));
            // copyIn creates a private per-run copy; the cached original is never mounted into user space.
            command.put("copyIn", Map.of(language.artifact(), Map.of("fileId", artifactId)));
            command.put("copyOutCached", List.of("stdout"));
            JSONObject execution = client.run(command, clockMs);
            Path output = null;
            try {
                checkInfrastructure(execution);
                result.setExecutedCaseCount(i + 1);
                result.setUseTime(Math.max(result.getUseTime(), nanosToMillis(execution.getLongValue("time"))));
                result.setUseMemory(Math.max(result.getUseMemory(), execution.getLongValue("memory")));
                CodeRunStatus status = runStatus(execution);
                UserExeResult detail = new UserExeResult();
                detail.setCaseId(test.caseId());
                detail.setInput(preview(test.input()));
                detail.setOutput(preview(test.expected()));
                detail.setCustom(sampleRun && test.expected() == null);
                if (!sampleRun && test.expected() == null) throw new IllegalStateException("Missing standard answer");
                if (status != CodeRunStatus.SUCCEED) {
                    detail.setPassed(false);
                    detail.setMessage(execution.getString("status") + ": " + diagnostic(execution));
                    result.setRunStatus(status);
                    result.setExeMessage(detail.getMessage());
                    result.setAllCasesPassed(false);
                    addDetail(details, detail, true);
                    break;
                }
                String stdoutId = execution.getJSONObject("fileIds") == null ? null
                        : execution.getJSONObject("fileIds").getString("stdout");
                if (stdoutId == null) throw new IllegalStateException("Runner did not cache stdout");
                output = client.download(stdoutId, config.getOutputLimitBytes(), deadline);
                JSONObject files = execution.getJSONObject("files");
                String stderr = files == null ? null : files.getString("stderr");
                long bytes = Files.size(output) + (stderr == null ? 0
                        : stderr.getBytes(java.nio.charset.StandardCharsets.UTF_8).length);
                totalOutput += bytes;
                if (totalOutput > config.getTotalOutputLimitBytes()) {
                    result.setRunStatus(CodeRunStatus.FAILED);
                    result.setExeMessage("整次提交输出超出限制");
                    result.setAllCasesPassed(false);
                    break;
                }
                boolean passed = checkOutput(checker, test.expected(), output, deadline);
                try (var reader = Files.newBufferedReader(output)) {
                    char[] chars = new char[config.getPreviewChars() + 1];
                    int length = 0, n;
                    while (length < chars.length && (n = reader.read(chars, length, chars.length - length)) != -1) length += n;
                    detail.setExeOutput(new String(chars, 0, Math.min(length, config.getPreviewChars())));
                    detail.setTruncated(length > config.getPreviewChars()
                            || isLong(test.input()) || isLong(test.expected()));
                }
                detail.setPassed(detail.getCustom() ? null : passed);
                detail.setMessage(passed ? "Accepted" : "Wrong Answer");
                addDetail(details, detail, !passed);
                if (!passed) {
                    result.setAllCasesPassed(false);
                    if (!sampleRun) break;
                }
                if (totalOutput == config.getTotalOutputLimitBytes() && i + 1 < count) {
                    result.setRunStatus(CodeRunStatus.FAILED);
                    result.setExeMessage("整次提交输出预算耗尽");
                    result.setAllCasesPassed(false);
                    break;
                }
            } catch (IOException e) {
                throw new IllegalStateException("Cannot check sandbox output", e);
            } finally {
                GoJudgeClient.deleteLocal(output);
                client.deleteResultFiles(execution);
            }
        }
        return result;
    }

    private Map<String, Object> command(List<String> args, String stdin, long cpuMs, long memory,
                                         long clockMs, long outputLimit) {
        if (clockMs <= 0 || outputLimit <= 0) throw new IllegalStateException("Sandbox execution budget exhausted");
        Map<String, Object> command = new LinkedHashMap<>();
        command.put("args", args);
        // Never inherit the backend process environment (DB/MQ credentials, API tokens, JAVA_TOOL_OPTIONS).
        command.put("env", List.of("PATH=/usr/local/bin:/usr/bin:/bin", "HOME=/w", "LANG=C.UTF-8",
                "GOCACHE=/tmp/go-cache", "GOPATH=/tmp/go", "GOMAXPROCS=1", "GOPROXY=off"));
        command.put("files", List.of(Map.of("content", stdin == null ? "" : stdin),
                Map.of("name", "stdout", "max", outputLimit), Map.of("name", "stderr", "max", 65536)));
        command.put("cpuLimit", TimeUnit.MILLISECONDS.toNanos(cpuMs));
        command.put("clockLimit", TimeUnit.MILLISECONDS.toNanos(clockMs));
        command.put("memoryLimit", memory);
        command.put("procLimit", config.getProcessLimit());
        command.put("cpuRateLimit", config.getCpuRateLimit());
        command.put("copyOutMax", outputLimit);
        // strictMemoryLimit adds RLIMIT_DATA, which is unsuitable for JVM address-space reservation.
        command.put("strictMemoryLimit", false);
        return command;
    }

    private int caseCount(JudgeSubmitDTO submission) {
        int count;
        if (submission.getTestCaseSetId() != null) {
            count = cases.count(submission.getTestCaseSetId());
            if (submission.getTestCaseCount() == null || submission.getTestCaseCount() != count) {
                throw new IllegalStateException("Test set manifest count mismatch");
            }
        } else {
            if (submission.getInputList() == null || submission.getOutputList() == null
                    || submission.getInputList().size() != submission.getOutputList().size()) {
                throw new IllegalArgumentException("Invalid inline test cases");
            }
            count = submission.getInputList().size();
        }
        if (count < 1 || count > config.getMaxCases()) throw new IllegalArgumentException("Invalid test case count");
        return count;
    }

    private JudgeCaseStore.TestCase readCase(JudgeSubmitDTO submission, int index) {
        return submission.getTestCaseSetId() == null
                ? new JudgeCaseStore.TestCase(JudgeCaseStore.caseId(index), submission.getInputList().get(index),
                        submission.getOutputList().get(index))
                : cases.read(submission.getTestCaseSetId(), index);
    }

    private void addDetail(List<UserExeResult> details, UserExeResult detail, boolean failure) {
        if (details.size() < config.getMaxCaseDetails()) details.add(detail);
        else if (failure) details.set(details.size() - 1, detail);
    }

    private boolean checkOutput(String checker, String expected, Path output, long deadline) throws IOException {
        boolean acquired = false;
        try {
            acquired = checkerSlot.tryAcquire(remaining(deadline), TimeUnit.MILLISECONDS);
            if (!acquired) throw new IllegalStateException("Output checker queue deadline exceeded");
            return OutputChecker.check(checker, expected, output,
                    Math.min(deadline, System.nanoTime() + TimeUnit.MILLISECONDS.toNanos(config.getCheckerTimeMs())));
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Output checker interrupted", e);
        } finally {
            if (acquired) checkerSlot.release();
        }
    }

    private CodeRunStatus runStatus(JSONObject result) {
        return switch (result.getString("status")) {
            case "Accepted" -> CodeRunStatus.SUCCEED;
            case "Time Limit Exceeded" -> CodeRunStatus.OUT_OF_TIME;
            case "Memory Limit Exceeded" -> CodeRunStatus.OUT_OF_MEMORY;
            default -> CodeRunStatus.FAILED;
        };
    }

    private void checkInfrastructure(JSONObject result) {
        if (List.of("Internal Error", "File Error").contains(result.getString("status"))) {
            throw new IllegalStateException("Sandbox infrastructure error: " + result.getString("status"));
        }
    }

    private String diagnostic(JSONObject result) {
        JSONObject files = result.getJSONObject("files");
        return preview(files == null ? result.getString("error") : files.getString("stderr"));
    }

    private String preview(String text) {
        return text == null ? null : text.substring(0, Math.min(text.length(), config.getPreviewChars()));
    }
    private boolean isLong(String text) { return text != null && text.length() > config.getPreviewChars(); }
    private long remaining(long deadline) { return Math.max(0, TimeUnit.NANOSECONDS.toMillis(deadline - System.nanoTime())); }
    private long nanosToMillis(long nanos) { return (nanos + 999999) / 1000000; }
    private long requireLimit(Long value, long max, String name) {
        if (value == null || value < 1 || value > max) throw new IllegalArgumentException("Invalid " + name);
        return value;
    }
}
