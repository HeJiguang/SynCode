package com.sintao.job.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.sintao.common.core.constants.Constants;
import com.sintao.common.core.enums.ExamAttemptStatus;
import com.sintao.common.core.enums.ExamGradeStatus;
import com.sintao.common.core.enums.ExamStatus;
import com.sintao.common.core.enums.JudgeAsyncStatus;
import com.sintao.common.core.enums.QuestionResType;
import com.sintao.common.core.enums.QuestionType;
import com.sintao.common.core.enums.ResultCode;
import com.sintao.job.domain.exam.ExamAnswer;
import com.sintao.job.domain.exam.ExamAttempt;
import com.sintao.job.domain.exam.Exam;
import com.sintao.job.domain.exam.ExamAuditEvent;
import com.sintao.job.domain.exam.ExamGrade;
import com.sintao.job.domain.exam.ExamGradeItem;
import com.sintao.job.domain.exam.ExamVersionQuestion;
import com.sintao.job.domain.exam.IntegrityEvent;
import com.sintao.job.domain.user.UserSubmit;
import com.sintao.job.mapper.exam.ExamAnswerMapper;
import com.sintao.job.mapper.exam.ExamAttemptMapper;
import com.sintao.job.mapper.exam.ExamAuditEventMapper;
import com.sintao.job.mapper.exam.ExamGradeItemMapper;
import com.sintao.job.mapper.exam.ExamGradeMapper;
import com.sintao.job.mapper.exam.ExamMapper;
import com.sintao.job.mapper.exam.ExamVersionQuestionMapper;
import com.sintao.job.mapper.exam.IntegrityEventMapper;
import com.sintao.job.mapper.user.UserSubmitMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.time.Clock;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.ArrayList;
import java.util.HashSet;

@Service
public class TrustedExamReconciliationService {

    private static final int BATCH_SIZE = 200;

    private final ExamAttemptMapper attemptMapper;
    private final ExamMapper examMapper;
    private final ExamAuditEventMapper auditMapper;
    private final IntegrityEventMapper integrityEventMapper;
    private final ExamAnswerMapper answerMapper;
    private final ExamVersionQuestionMapper versionQuestionMapper;
    private final ExamGradeMapper gradeMapper;
    private final ExamGradeItemMapper gradeItemMapper;
    private final UserSubmitMapper userSubmitMapper;
    private final Clock clock;
    private final int integrityRetentionDays;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public TrustedExamReconciliationService(ExamAttemptMapper attemptMapper,
                                            ExamMapper examMapper,
                                            ExamAuditEventMapper auditMapper,
                                            IntegrityEventMapper integrityEventMapper,
                                            ExamAnswerMapper answerMapper,
                                            ExamVersionQuestionMapper versionQuestionMapper,
                                            ExamGradeMapper gradeMapper,
                                            ExamGradeItemMapper gradeItemMapper,
                                            UserSubmitMapper userSubmitMapper,
                                            Clock clock,
                                            @Value("${syncode.exam.integrity-retention-days:180}") int integrityRetentionDays) {
        this.attemptMapper = attemptMapper;
        this.examMapper = examMapper;
        this.auditMapper = auditMapper;
        this.integrityEventMapper = integrityEventMapper;
        this.answerMapper = answerMapper;
        this.versionQuestionMapper = versionQuestionMapper;
        this.gradeMapper = gradeMapper;
        this.gradeItemMapper = gradeItemMapper;
        this.userSubmitMapper = userSubmitMapper;
        this.clock = clock;
        this.integrityRetentionDays = integrityRetentionDays;
    }

    @Transactional
    public int finalizeExpiredAttempts() {
        LocalDateTime now = now();
        List<ExamAttempt> expired = attemptMapper.selectList(new LambdaQueryWrapper<ExamAttempt>()
                .eq(ExamAttempt::getStatus, ExamAttemptStatus.IN_PROGRESS.getCode())
                .le(ExamAttempt::getDeadlineTime, now)
                .orderByAsc(ExamAttempt::getDeadlineTime)
                .last("limit " + BATCH_SIZE));
        int finalized = 0;
        for (ExamAttempt attempt : expired) {
            attempt.setStatus(ExamAttemptStatus.TIMED_OUT.getCode());
            attempt.setSubmittedTime(now);
            attempt.setFinalizedTime(now);
            attempt.setFinalizationReason("DEADLINE");
            attempt.setFinalizationKey("timeout:" + attempt.getAttemptId() + ":" + attempt.getDeadlineTime());
            attempt.setLastActiveTime(now);
            attempt.setUpdateTime(now);
            attempt.setRowVersion(attempt.getRowVersion() + 1);
            int rows = attemptMapper.update(attempt, new UpdateWrapper<ExamAttempt>()
                    .eq("attempt_id", attempt.getAttemptId())
                    .eq("status", ExamAttemptStatus.IN_PROGRESS.getCode()));
            if (rows == 0) {
                continue;
            }
            finalized++;
            answerMapper.update(null, new UpdateWrapper<ExamAnswer>()
                    .eq("attempt_id", attempt.getAttemptId())
                    .isNull("frozen_time")
                    .set("frozen_time", now)
                    .set("update_time", now));
            ensureGrade(attempt, now);
        }
        return finalized;
    }

    @Transactional
    public int aggregateTerminalGrades() {
        List<ExamAttempt> attempts = attemptMapper.selectList(new LambdaQueryWrapper<ExamAttempt>()
                .in(ExamAttempt::getStatus,
                        ExamAttemptStatus.SUBMITTED.getCode(), ExamAttemptStatus.TIMED_OUT.getCode())
                .orderByAsc(ExamAttempt::getFinalizedTime)
                .last("limit " + BATCH_SIZE));
        int ready = 0;
        for (ExamAttempt attempt : attempts) {
            if (aggregate(attempt)) {
                ready++;
            }
        }
        return ready;
    }

    @Transactional
    public int finishEndedExams() {
        LocalDateTime now = now();
        List<Exam> ended = examMapper.selectList(new LambdaQueryWrapper<Exam>()
                .in(Exam::getStatus, ExamStatus.PUBLISHED.getCode(), ExamStatus.ACTIVE.getCode())
                .le(Exam::getEndTime, now)
                .orderByAsc(Exam::getEndTime)
                .last("limit " + BATCH_SIZE));
        int finished = 0;
        for (Exam exam : ended) {
            int rows = examMapper.update(null, new UpdateWrapper<Exam>()
                    .eq("exam_id", exam.getExamId())
                    .in("status", ExamStatus.PUBLISHED.getCode(), ExamStatus.ACTIVE.getCode())
                    .set("status", ExamStatus.FINISHED.getCode())
                    .set("finished_time", now)
                    .setSql("row_version = row_version + 1"));
            if (rows > 0) {
                finished++;
            }
        }
        return finished;
    }

    @Transactional
    public int releaseScheduledResults() {
        LocalDateTime now = now();
        List<Exam> scheduled = examMapper.selectList(new LambdaQueryWrapper<Exam>()
                .eq(Exam::getStatus, ExamStatus.FINISHED.getCode())
                .eq(Exam::getResultReleasePolicy, "SCHEDULED")
                .le(Exam::getResultReleaseTime, now)
                .orderByAsc(Exam::getResultReleaseTime)
                .last("limit " + BATCH_SIZE));
        int released = 0;
        for (Exam exam : scheduled) {
            List<ExamAttempt> attempts = attemptMapper.selectList(new LambdaQueryWrapper<ExamAttempt>()
                    .eq(ExamAttempt::getExamId, exam.getExamId()));
            if (attempts.isEmpty()) {
                continue;
            }
            List<ExamGrade> grades = gradeMapper.selectList(new LambdaQueryWrapper<ExamGrade>()
                    .in(ExamGrade::getAttemptId, attempts.stream().map(ExamAttempt::getAttemptId).toList())
                    .eq(ExamGrade::getCurrentFlag, 1));
            if (grades.size() != attempts.size() || grades.stream().anyMatch(grade ->
                    ExamGradeStatus.fromCode(grade.getStatus()) != ExamGradeStatus.READY)) {
                continue;
            }
            int examRows = examMapper.update(null, new UpdateWrapper<Exam>()
                    .eq("exam_id", exam.getExamId())
                    .eq("status", ExamStatus.FINISHED.getCode())
                    .set("status", ExamStatus.RESULT_RELEASED.getCode())
                    .set("result_released_time", now)
                    .setSql("row_version = row_version + 1"));
            if (examRows == 0) {
                continue;
            }
            for (ExamGrade grade : grades) {
                grade.setStatus(ExamGradeStatus.RELEASED.getCode());
                grade.setReleasedTime(now);
                grade.setUpdateBy(Constants.SYSTEM_USER_ID);
                grade.setUpdateTime(now);
                gradeMapper.updateById(grade);
            }
            auditScheduledRelease(exam.getExamId(), grades.size(), now);
            released++;
        }
        return released;
    }

    @Transactional
    public int purgeExpiredIntegrityEvidence() {
        LocalDateTime cutoff = now().minusDays(integrityRetentionDays);
        return integrityEventMapper.delete(new LambdaQueryWrapper<IntegrityEvent>()
                .lt(IntegrityEvent::getServerReceivedTime, cutoff)
                .last("limit " + BATCH_SIZE));
    }

    private boolean aggregate(ExamAttempt attempt) {
        ExamGrade grade = gradeMapper.selectOne(new LambdaQueryWrapper<ExamGrade>()
                .eq(ExamGrade::getAttemptId, attempt.getAttemptId())
                .eq(ExamGrade::getCurrentFlag, 1));
        if (grade != null) {
            ExamGradeStatus gradeStatus = ExamGradeStatus.fromCode(grade.getStatus());
            if (gradeStatus == ExamGradeStatus.READY || gradeStatus == ExamGradeStatus.RELEASED) {
                return false;
            }
        }
        List<UserSubmit> submissions = userSubmitMapper.selectList(new LambdaQueryWrapper<UserSubmit>()
                .eq(UserSubmit::getAttemptId, attempt.getAttemptId())
                .eq(UserSubmit::getSubmitKind, "FORMAL")
                .orderByAsc(UserSubmit::getCreateTime));
        if (submissions.stream().anyMatch(item -> Objects.equals(
                item.getJudgeStatus(), JudgeAsyncStatus.WAITING.getValue()))) {
            return false;
        }
        LocalDateTime now = now();
        if (grade == null) {
            grade = ensureGrade(attempt, now);
        }
        List<ExamVersionQuestion> questions = versionQuestionMapper.selectList(
                new LambdaQueryWrapper<ExamVersionQuestion>()
                        .eq(ExamVersionQuestion::getVersionId, attempt.getVersionId())
                        .orderByAsc(ExamVersionQuestion::getQuestionOrder));
        Map<Long, UserSubmit> latestCompleted = new HashMap<>();
        submissions.stream()
                .filter(item -> Objects.equals(item.getJudgeStatus(), JudgeAsyncStatus.SUCCESS.getValue()))
                .sorted(Comparator.comparing(UserSubmit::getCreateTime,
                        Comparator.nullsFirst(Comparator.naturalOrder())))
                .forEach(item -> latestCompleted.put(item.getVersionQuestionId(), item));
        Map<Long, ExamAnswer> answers = new HashMap<>();
        answerMapper.selectList(new LambdaQueryWrapper<ExamAnswer>()
                        .eq(ExamAnswer::getAttemptId, attempt.getAttemptId()))
                .forEach(answer -> answers.put(answer.getVersionQuestionId(), answer));

        gradeItemMapper.delete(new LambdaQueryWrapper<ExamGradeItem>()
                .eq(ExamGradeItem::getGradeId, grade.getGradeId()));
        int total = 0;
        int max = 0;
        boolean requiresManualReview = false;
        boolean hasAuto = false;
        for (ExamVersionQuestion question : questions) {
            QuestionType type = QuestionType.from(question.getQuestionType());
            UserSubmit submission = type == QuestionType.PROGRAMMING
                    ? latestCompleted.get(question.getVersionQuestionId()) : null;
            boolean passed = type == QuestionType.PROGRAMMING
                    ? submission != null && Objects.equals(submission.getPass(), QuestionResType.PASS.getValue())
                    : type.isObjective() && objectiveAnswerMatches(
                            answers.get(question.getVersionQuestionId()), question.getGradingConfigJson(), type);
            boolean manual = !type.isObjective() && type != QuestionType.PROGRAMMING;
            int awarded = !manual && passed ? question.getScore() : 0;
            requiresManualReview |= manual;
            hasAuto |= !manual;
            total += awarded;
            max += question.getScore();
            ExamGradeItem item = new ExamGradeItem();
            item.setGradeId(grade.getGradeId());
            item.setVersionQuestionId(question.getVersionQuestionId());
            item.setSubmitId(submission == null ? null : submission.getSubmitId());
            item.setAwardedScore(awarded);
            item.setMaxScore(question.getScore());
            item.setGradingMode(manual ? "MANUAL" : "AUTO");
            item.setCreateBy(Constants.SYSTEM_USER_ID);
            item.setCreateTime(now);
            gradeItemMapper.insert(item);
            if (type == QuestionType.PROGRAMMING && passed && submission.getAnswerId() != null) {
                answerMapper.update(null, new UpdateWrapper<ExamAnswer>()
                        .eq("answer_id", submission.getAnswerId())
                        .set("latest_accepted_submit_id", submission.getSubmitId())
                        .set("update_time", now));
            }
        }
        grade.setStatus(requiresManualReview ? ExamGradeStatus.NEEDS_REVIEW.getCode() : ExamGradeStatus.READY.getCode());
        grade.setTotalScore(total);
        grade.setMaxScore(max);
        grade.setCalculationSource(requiresManualReview ? (hasAuto ? "MIXED" : "MANUAL") : "AUTO");
        grade.setCalculatedTime(now);
        grade.setUpdateBy(Constants.SYSTEM_USER_ID);
        grade.setUpdateTime(now);
        gradeMapper.updateById(grade);
        return true;
    }

    private boolean objectiveAnswerMatches(ExamAnswer answer, String gradingConfigJson, QuestionType type) {
        if (answer == null || answer.getAnswerContent() == null || gradingConfigJson == null) return false;
        try {
            JsonNode config = objectMapper.readTree(gradingConfigJson);
            JsonNode correctNode = config.path("correctAnswers");
            if (!correctNode.isArray() || correctNode.isEmpty()) return false;
            List<String> correct = new ArrayList<>();
            for (JsonNode item : correctNode) correct.add(item.asText().trim());
            List<String> actual = parseCandidateAnswers(answer.getAnswerContent());
            boolean caseSensitive = config.path("caseSensitive").asBoolean(false);
            if (!caseSensitive) {
                correct = correct.stream().map(value -> value.toLowerCase(java.util.Locale.ROOT)).toList();
                actual = actual.stream().map(value -> value.toLowerCase(java.util.Locale.ROOT)).toList();
            }
            if (type == QuestionType.FILL_BLANK) return correct.equals(actual);
            return new HashSet<>(correct).equals(new HashSet<>(actual)) && correct.size() == actual.size();
        } catch (Exception exception) {
            return false;
        }
    }

    private List<String> parseCandidateAnswers(String content) throws Exception {
        JsonNode node = objectMapper.readTree(content);
        if (node.isArray()) {
            List<String> values = new ArrayList<>();
            node.forEach(item -> values.add(item.asText().trim()));
            return values;
        }
        return List.of(node.asText().trim());
    }

    private ExamGrade ensureGrade(ExamAttempt attempt, LocalDateTime now) {
        ExamGrade grade = gradeMapper.selectOne(new LambdaQueryWrapper<ExamGrade>()
                .eq(ExamGrade::getAttemptId, attempt.getAttemptId())
                .eq(ExamGrade::getCurrentFlag, 1));
        if (grade != null) {
            return grade;
        }
        List<ExamVersionQuestion> questions = versionQuestionMapper.selectList(
                new LambdaQueryWrapper<ExamVersionQuestion>()
                        .eq(ExamVersionQuestion::getVersionId, attempt.getVersionId()));
        grade = new ExamGrade();
        grade.setAttemptId(attempt.getAttemptId());
        grade.setRevision(1);
        grade.setStatus(ExamGradeStatus.WAITING_FOR_JUDGE.getCode());
        grade.setTotalScore(0);
        grade.setMaxScore(questions.stream().mapToInt(ExamVersionQuestion::getScore).sum());
        grade.setCalculationSource("AUTO");
        grade.setCurrentFlag(1);
        grade.setCreateBy(Constants.SYSTEM_USER_ID);
        grade.setCreateTime(now);
        gradeMapper.insert(grade);
        return grade;
    }

    private void auditScheduledRelease(Long examId, int gradeCount, LocalDateTime now) {
        ExamAuditEvent event = new ExamAuditEvent();
        event.setExamId(examId);
        event.setActorId(Constants.SYSTEM_USER_ID);
        event.setActorType("SYSTEM");
        event.setAction("RESULTS_RELEASED");
        event.setRequestId("scheduled-release:" + examId);
        event.setResultCode(ResultCode.SUCCESS.getCode());
        event.setMetadataJson("{\"policy\":\"SCHEDULED\",\"gradeCount\":" + gradeCount + "}");
        event.setServerTime(now);
        auditMapper.insert(event);
    }

    private LocalDateTime now() {
        return LocalDateTime.ofInstant(clock.instant(), ZoneOffset.UTC);
    }
}
