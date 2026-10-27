package com.sintao.judge.sandbox;

import com.alibaba.fastjson2.JSONObject;
import com.sintao.api.domain.dto.JudgeSubmitDTO;
import com.sintao.common.core.enums.CodeRunStatus;
import com.sintao.common.redis.service.JudgeCaseStore;
import com.sintao.judge.config.GoJudgeProperties;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.mockito.ArgumentCaptor;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class GoJudgeSandboxServiceTest {
    @TempDir Path temp;
    GoJudgeClient client = mock(GoJudgeClient.class);
    JudgeCaseStore store = mock(JudgeCaseStore.class);
    GoJudgeProperties config = new GoJudgeProperties();

    private JudgeSubmitDTO submission() {
        JudgeSubmitDTO dto = new JudgeSubmitDTO();
        dto.setProgramType(0);
        dto.setTimeLimit(2000L);
        dto.setSpaceLimit(262144L);
        dto.setUserCode("public class Main { public static void main(String[] a) {} }");
        dto.setInputList(List.of("  a\n\n", ""));
        dto.setOutputList(List.of("answer", "answer"));
        return dto;
    }

    private JSONObject compiled() {
        return JSONObject.of("status", "Accepted", "fileIds", JSONObject.of("program.jar", "artifact1"));
    }

    private JSONObject executed(String id) {
        return JSONObject.of("status", "Accepted", "time", 1500000L, "memory", 12345678L,
                "fileIds", JSONObject.of("stdout", id));
    }

    private Path output(String name, String content) throws Exception {
        Path file = temp.resolve(name);
        Files.writeString(file, content);
        return file;
    }

    @Test void compilesOnceReusesCachedArtifactAndPreservesRawStdinAndPerQuestionLimits() throws Exception {
        JSONObject compile = compiled(), first = executed("stdout1"), second = executed("stdout2");
        when(client.run(anyMap(), anyLong())).thenReturn(compile, first, second);
        Path one = output("one", "answer\n"), two = output("two", "answer");
        when(client.download(eq("stdout1"), anyLong(), anyLong())).thenReturn(one);
        when(client.download(eq("stdout2"), anyLong(), anyLong())).thenReturn(two);

        var result = new GoJudgeSandboxService(client, store, config).execute(submission(), false);

        assertTrue(result.getAllCasesPassed());
        assertEquals(2, result.getExecutedCaseCount());
        assertEquals(List.of("case-1", "case-2"), result.getCaseResults().stream().map(x -> x.getCaseId()).toList());
        assertEquals(2L, result.getUseTime());
        assertEquals(12345678L, result.getUseMemory());
        ArgumentCaptor<Map<String, Object>> commands = ArgumentCaptor.forClass(Map.class);
        verify(client, times(3)).run(commands.capture(), anyLong());
        List<Map<String, Object>> sent = commands.getAllValues();
        assertEquals(config.getCompileMemoryBytes(), sent.get(0).get("memoryLimit"));
        assertEquals(268435456L, sent.get(1).get("memoryLimit"));
        assertEquals(2000000000L, sent.get(1).get("cpuLimit"));
        assertEquals(6000000000L, sent.get(1).get("clockLimit"));
        assertEquals(Map.of("program.jar", Map.of("fileId", "artifact1")), sent.get(1).get("copyIn"));
        assertEquals(sent.get(1).get("copyIn"), sent.get(2).get("copyIn"));
        assertEquals(Map.of("content", "  a\n\n"), ((List<?>) sent.get(1).get("files")).get(0));
        assertEquals(Map.of("content", ""), ((List<?>) sent.get(2).get("files")).get(0));
        assertFalse(Files.exists(one));
        assertFalse(Files.exists(two));
        verify(client).deleteResultFiles(compile);
        verify(client).deleteResultFiles(first);
        verify(client).deleteResultFiles(second);
    }

    @Test void checksFullOutputBeforeTruncatingPreviewAndStopsAtFirstWrongAnswer() throws Exception {
        config.setPreviewChars(3);
        JudgeSubmitDTO dto = submission();
        dto.setOutputList(List.of("answer x", "answer"));
        JSONObject compile = compiled(), execution = executed("stdout1");
        when(client.run(anyMap(), anyLong())).thenReturn(compile, execution);
        Path file = output("actual", "answer y");
        when(client.download(anyString(), anyLong(), anyLong())).thenReturn(file);

        var result = new GoJudgeSandboxService(client, store, config).execute(dto, false);

        assertFalse(result.getAllCasesPassed());
        assertEquals(1, result.getExecutedCaseCount());
        assertEquals("ans", result.getCaseResults().get(0).getExeOutput());
        assertTrue(result.getCaseResults().get(0).getTruncated());
        verify(client, times(2)).run(anyMap(), anyLong());
        verify(client).deleteResultFiles(compile);
        verify(client).deleteResultFiles(execution);
        assertFalse(Files.exists(file));
    }

    @Test void fetchesReferencedCasesOneAtATimeAndDoesNotReadLaterCasesAfterFailure() throws Exception {
        JudgeSubmitDTO dto = submission();
        dto.setTestCaseSetId("a".repeat(64));
        dto.setTestCaseCount(500);
        dto.setInputList(null);
        dto.setOutputList(null);
        when(store.count(dto.getTestCaseSetId())).thenReturn(500);
        when(store.read(dto.getTestCaseSetId(), 0)).thenReturn(new JudgeCaseStore.TestCase("case-1", "input", "yes"));
        when(client.run(anyMap(), anyLong())).thenReturn(compiled(), executed("stdout1"));
        when(client.download(anyString(), anyLong(), anyLong())).thenReturn(output("wrong", "no"));

        var result = new GoJudgeSandboxService(client, store, config).execute(dto, false);
        assertFalse(result.getAllCasesPassed());
        verify(store, times(1)).read(anyString(), anyInt());
    }

    @Test void mapsMemoryTimeoutAndOutputFailuresAndAlwaysReleasesCachedFiles() {
        for (String status : List.of("Memory Limit Exceeded", "Time Limit Exceeded", "Output Limit Exceeded")) {
            reset(client);
            JSONObject compile = compiled();
            JSONObject execution = JSONObject.of("status", status, "fileIds", JSONObject.of("stdout", "partial"));
            when(client.run(anyMap(), anyLong())).thenReturn(compile, execution);
            var result = new GoJudgeSandboxService(client, store, config).execute(submission(), false);
            assertEquals(status.startsWith("Memory") ? CodeRunStatus.OUT_OF_MEMORY
                    : status.startsWith("Time") ? CodeRunStatus.OUT_OF_TIME : CodeRunStatus.FAILED, result.getRunStatus());
            verify(client).deleteResultFiles(compile);
            verify(client).deleteResultFiles(execution);
            verify(client, never()).download(anyString(), anyLong(), anyLong());
        }
    }

    @Test void infrastructureFailureNeverBecomesWrongAnswerAndStillReleasesArtifact() {
        JSONObject compile = compiled();
        when(client.run(anyMap(), anyLong())).thenReturn(compile)
                .thenThrow(new IllegalStateException("connection lost"));
        assertThrows(IllegalStateException.class,
                () -> new GoJudgeSandboxService(client, store, config).execute(submission(), false));
        verify(client).deleteResultFiles(compile);
    }

    @Test void rejectsInvalidLimitsBeforeStartingExecution() {
        JudgeSubmitDTO dto = submission();
        dto.setSpaceLimit(999999999L);
        assertThrows(IllegalArgumentException.class,
                () -> new GoJudgeSandboxService(client, store, config).execute(dto, false));
        verifyNoInteractions(client);
    }

    @Test void boundsDetailsAndKeepsTheLateFailureWhileReleasingEveryOutput() throws Exception {
        config.setMaxCaseDetails(2);
        JudgeSubmitDTO dto = submission();
        dto.setInputList(java.util.Collections.nCopies(10, "input"));
        var answers = new java.util.ArrayList<>(java.util.Collections.nCopies(10, "answer"));
        answers.set(9, "different");
        dto.setOutputList(answers);
        when(client.run(anyMap(), anyLong())).thenReturn(compiled(), executed("stdout1"));
        when(client.download(anyString(), anyLong(), anyLong())).thenAnswer(inv -> {
            Path file = Files.createTempFile(temp, "actual", ".txt");
            Files.writeString(file, "answer");
            return file;
        });
        var result = new GoJudgeSandboxService(client, store, config).execute(dto, false);
        assertFalse(result.getAllCasesPassed());
        assertEquals(10, result.getExecutedCaseCount());
        assertEquals(2, result.getCaseResults().size());
        assertEquals("case-10", result.getCaseResults().get(1).getCaseId());
        try (var files = Files.list(temp)) { assertEquals(0, files.count()); }
        verify(client, times(11)).run(anyMap(), anyLong());
    }
}
