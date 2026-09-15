package com.sintao.friend.service.exam.impl;

import cn.hutool.crypto.digest.DigestUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sintao.api.domain.dto.JudgeSubmitDTO;
import com.sintao.common.core.constants.Constants;
import com.sintao.common.core.enums.ExamAttemptStatus;
import com.sintao.common.core.enums.ExamGradeStatus;
import com.sintao.common.core.enums.ExamStatus;
import com.sintao.common.core.enums.JudgeAsyncStatus;
import com.sintao.common.core.enums.ProgramType;
import com.sintao.common.core.enums.QuestionResType;
import com.sintao.common.core.enums.ResultCode;
import com.sintao.common.core.utils.ThreadLocalUtil;
import com.sintao.common.redis.service.JudgeRuntimeStateService;
import com.sintao.common.security.exception.ServiceException;
import com.sintao.friend.domain.exam.Exam;
import com.sintao.friend.domain.exam.ExamAnswer;
import com.sintao.friend.domain.exam.ExamAttempt;
import com.sintao.friend.domain.exam.ExamAuditEvent;
import com.sintao.friend.domain.exam.ExamCommand;
import com.sintao.friend.domain.exam.ExamGrade;
import com.sintao.friend.domain.exam.ExamGradeItem;
import com.sintao.friend.domain.exam.IntegrityEvent;
import com.sintao.friend.domain.exam.ExamVersion;
import com.sintao.friend.domain.exam.ExamVersionQuestion;
import com.sintao.friend.domain.exam.dto.ExamSubmissionDTO;
import com.sintao.friend.domain.exam.dto.HeartbeatDTO;
import com.sintao.friend.domain.exam.dto.SaveAnswerDTO;
import com.sintao.friend.domain.exam.dto.StartExamDTO;
import com.sintao.friend.domain.exam.dto.IntegrityEventBatchDTO;
import com.sintao.friend.domain.exam.dto.IntegrityEventDTO;
import com.sintao.friend.domain.exam.vo.ExamAccessVO;
import com.sintao.friend.domain.exam.vo.ExamAnswerVO;
import com.sintao.friend.domain.exam.vo.ExamAttemptVO;
import com.sintao.friend.domain.exam.vo.ExamFinalizeVO;
import com.sintao.friend.domain.exam.vo.ExamSubmissionVO;
import com.sintao.friend.domain.exam.vo.HeartbeatVO;
import com.sintao.friend.domain.exam.vo.ExamGradeItemVO;
import com.sintao.friend.domain.exam.vo.ExamResultVO;
import com.sintao.friend.domain.exam.vo.IntegrityBatchResultVO;
import com.sintao.friend.domain.exam.vo.TrustedExamQuestionVO;
import com.sintao.friend.domain.user.User;
import com.sintao.friend.domain.user.UserExam;
import com.sintao.friend.domain.user.UserSubmit;
import com.sintao.friend.mapper.exam.ExamAnswerMapper;
import com.sintao.friend.mapper.exam.ExamAttemptMapper;
import com.sintao.friend.mapper.exam.ExamAuditEventMapper;
import com.sintao.friend.mapper.exam.ExamCommandMapper;
import com.sintao.friend.mapper.exam.ExamGradeMapper;
import com.sintao.friend.mapper.exam.ExamGradeItemMapper;
import com.sintao.friend.mapper.exam.IntegrityEventMapper;
import com.sintao.friend.mapper.exam.ExamMapper;
import com.sintao.friend.mapper.exam.ExamVersionMapper;
import com.sintao.friend.mapper.exam.ExamVersionQuestionMapper;
import com.sintao.friend.mapper.user.UserExamMapper;
import com.sintao.friend.mapper.user.UserMapper;
import com.sintao.friend.mapper.user.UserSubmitMapper;
import com.sintao.friend.rabbit.JudgeProducer;
import com.sintao.friend.service.exam.ITrustedExamService;
import com.sintao.friend.service.exam.ExamAttemptExpiredException;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

import java.time.Clock;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

@Service
@Slf4j
public class TrustedExamServiceImpl implements ITrustedExamService {

    private static final Set<String> SUBMIT_KINDS = Set.of("RUN", "FORMAL");
    private static final Set<String> INTEGRITY_EVENT_TYPES = Set.of(
            "FOCUS_LOST", "FULLSCREEN_EXIT", "PASTE", "COPY", "SESSION_CHANGE");
    private static final Set<String> INTEGRITY_METADATA_KEYS = Set.of(
            "durationMs", "visibilityState", "source", "target", "fullscreen");
    private static final int MAX_ANSWER_LENGTH = 262_144;

    private final ExamMapper examMapper;
    private final ExamVersionMapper examVersionMapper;
    private final ExamVersionQuestionMapper versionQuestionMapper;
    private final ExamAttemptMapper attemptMapper;
    private final ExamAnswerMapper answerMapper;
    private final ExamCommandMapper commandMapper;
    private final ExamAuditEventMapper auditMapper;
    private final ExamGradeMapper gradeMapper;
    private final ExamGradeItemMapper gradeItemMapper;
    private final IntegrityEventMapper integrityEventMapper;
    private final UserExamMapper userExamMapper;
    private final UserMapper userMapper;
    private final UserSubmitMapper userSubmitMapper;
    private final JudgeProducer judgeProducer;
    private final JudgeRuntimeStateService judgeRuntimeStateService;
    private final ObjectMapper objectMapper;
    private final Clock clock;
    private final String evidenceSalt;

    public TrustedExamServiceImpl(ExamMapper examMapper,
                                  ExamVersionMapper examVersionMapper,
                                  ExamVersionQuestionMapper versionQuestionMapper,
                                  ExamAttemptMapper attemptMapper,
                                  ExamAnswerMapper answerMapper,
                                  ExamCommandMapper commandMapper,
                                  ExamAuditEventMapper auditMapper,
                                  ExamGradeMapper gradeMapper,
                                  ExamGradeItemMapper gradeItemMapper,
                                  IntegrityEventMapper integrityEventMapper,
                                  UserExamMapper userExamMapper,
                                  UserMapper userMapper,
                                  UserSubmitMapper userSubmitMapper,
                                  JudgeProducer judgeProducer,
                                  JudgeRuntimeStateService judgeRuntimeStateService,
                                  ObjectMapper objectMapper,
                                  Clock clock,
                                  @Value("${trusted-exam.evidence-salt:${jwt.secret}}") String evidenceSalt) {
        this.examMapper = examMapper;
        this.examVersionMapper = examVersionMapper;
        this.versionQuestionMapper = versionQuestionMapper;
        this.attemptMapper = attemptMapper;
        this.answerMapper = answerMapper;
        this.commandMapper = commandMapper;
        this.auditMapper = auditMapper;
        this.gradeMapper = gradeMapper;
        this.gradeItemMapper = gradeItemMapper;
        this.integrityEventMapper = integrityEventMapper;
        this.userExamMapper = userExamMapper;
        this.userMapper = userMapper;
        this.userSubmitMapper = userSubmitMapper;
        this.judgeProducer = judgeProducer;
        this.judgeRuntimeStateService = judgeRuntimeStateService;
        this.objectMapper = objectMapper;
        this.clock = clock;
        this.evidenceSalt = evidenceSalt;
    }

    @Override
    public ExamAccessVO access(Long examId) {
        long userId = currentUserId();
        Exam exam = requirePublishedExam(examId);
        ExamVersion version = getVersion(exam.getCurrentVersionId());
        requireAuthorizedCandidate(examId, userId);
        requireEnabledUser(userId);
        LocalDateTime now = now();
        ExamAttempt attempt = findAttempt(version.getVersionId(), userId);
        ExamAccessVO result = new ExamAccessVO();
        result.setExamId(examId);
        result.setTitle(version.getTitle());
        result.setDescription(version.getDescription());
        result.setStatus(effectiveStatus(exam, version, now).name());
        result.setAuthorized(true);
        result.setServerNow(now);
        result.setStartAt(version.getStartTime());
        result.setLatestStartAt(version.getLatestStartTime());
        result.setEndAt(version.getEndTime());
        result.setDurationMinutes(version.getDurationMinutes());
        result.setTimezone(version.getTimezone());
        result.setPrivacyNotice("考试期间会记录会话标识、网络与浏览器摘要以及切屏等诚信事件；不采集剪贴板正文，证据默认保存 180 天，仅供人工复核，不自动认定作弊。");
        if (attempt != null) {
            result.setAttemptId(attempt.getAttemptId());
            result.setCanResume(ExamAttemptStatus.fromCode(attempt.getStatus()) == ExamAttemptStatus.IN_PROGRESS);
            result.setCanStart(false);
            result.setAllowedActions(result.isCanResume() ? List.of("RESUME") : List.of("VIEW_RECEIPT"));
            return result;
        }
        boolean inAdmissionWindow = !now.isBefore(version.getStartTime())
                && !now.isAfter(version.getLatestStartTime()) && now.isBefore(version.getEndTime());
        result.setCanStart(inAdmissionWindow);
        result.setAllowedActions(inAdmissionWindow ? List.of("START") : List.of());
        return result;
    }

    @Override
    @Transactional
    public ExamAttemptVO start(Long examId, StartExamDTO request, String idempotencyKey,
                               String requestId, String ipAddress, String userAgent) {
        long userId = currentUserId();
        validateKey(idempotencyKey, "Idempotency-Key");
        validateSession(request == null ? null : request.getSessionId());
        String requestHash = DigestUtil.sha256Hex("START:" + examId + ":" + request.getSessionId());
        ExamCommand existingCommand = findCommand("START", userId, idempotencyKey);
        if (existingCommand != null) {
            return replay(existingCommand, requestHash, ExamAttemptVO.class, true);
        }
        ExamCommand command = beginCommand("START", userId, idempotencyKey, requestHash, "ATTEMPT");
        LocalDateTime now = now();
        Exam exam = examMapper.selectByIdForUpdate(examId);
        if (exam == null) {
            throw new ServiceException(ResultCode.EXAM_NOT_EXISTS);
        }
        reconcileExamState(exam, now);
        if (ExamStatus.fromCode(exam.getStatus()) == ExamStatus.CANCELLED) {
            throw new ServiceException(ResultCode.EXAM_CANCELLED);
        }
        if (exam.getCurrentVersionId() == null || ExamStatus.fromCode(exam.getStatus()) == ExamStatus.DRAFT) {
            throw new ServiceException(ResultCode.EXAM_NOT_PUBLISHED);
        }
        ExamVersion version = getVersion(exam.getCurrentVersionId());
        requireAuthorizedCandidate(examId, userId);
        requireEnabledUser(userId);
        ExamAttempt existingAttempt = findAttempt(version.getVersionId(), userId);
        if (existingAttempt != null) {
            ExamAttemptVO result = attemptVO(existingAttempt, version, true, now);
            finishCommand(command, existingAttempt.getAttemptId(), result, now);
            return result;
        }
        if (now.isBefore(version.getStartTime())) {
            throw new ServiceException(ResultCode.EXAM_ACCESS_TOO_EARLY,
                    Map.of("serverNow", now, "startAt", version.getStartTime()));
        }
        if (now.isAfter(version.getLatestStartTime()) || !now.isBefore(version.getEndTime())) {
            throw new ServiceException(ResultCode.EXAM_ADMISSION_CLOSED,
                    Map.of("serverNow", now, "latestStartAt", version.getLatestStartTime()));
        }

        ExamAttempt attempt = new ExamAttempt();
        attempt.setExamId(examId);
        attempt.setVersionId(version.getVersionId());
        attempt.setUserId(userId);
        attempt.setStatus(ExamAttemptStatus.IN_PROGRESS.getCode());
        attempt.setRowVersion(0);
        attempt.setStartedTime(now);
        LocalDateTime durationDeadline = now.plusMinutes(version.getDurationMinutes());
        attempt.setDeadlineTime(durationDeadline.isBefore(version.getEndTime()) ? durationDeadline : version.getEndTime());
        attempt.setLastActiveTime(now);
        attempt.setCurrentSessionId(request.getSessionId());
        attempt.setFirstIpHash(hashEvidence(ipAddress));
        attempt.setLatestIpHash(hashEvidence(ipAddress));
        attempt.setUserAgentHash(hashEvidence(userAgent));
        attempt.setRiskLevel(0);
        attempt.setCreateTime(now);
        try {
            attemptMapper.insert(attempt);
        } catch (DuplicateKeyException exception) {
            attempt = findAttempt(version.getVersionId(), userId);
            if (attempt == null) {
                throw exception;
            }
        }
        ExamAttemptVO result = attemptVO(attempt, version, false, now);
        finishCommand(command, attempt.getAttemptId(), result, now);
        audit(examId, attempt.getAttemptId(), userId, "ATTEMPT_STARTED",
                safeRequestId(requestId, idempotencyKey), Map.of("versionId", version.getVersionId()));
        return result;
    }

    @Override
    @Transactional
    public ExamAttemptVO current(Long examId) {
        long userId = currentUserId();
        Exam exam = requirePublishedExam(examId);
        ExamVersion version = getVersion(exam.getCurrentVersionId());
        ExamAttempt found = findAttempt(version.getVersionId(), userId);
        if (found == null) {
            throw new ServiceException(ResultCode.EXAM_ATTEMPT_NOT_FOUND);
        }
        ExamAttempt attempt = attemptMapper.selectByIdForUpdate(found.getAttemptId());
        LocalDateTime now = now();
        if (isExpired(attempt, now)) {
            finalizeInternal(attempt, ExamAttemptStatus.TIMED_OUT, "DEADLINE",
                    "timeout:" + attempt.getAttemptId() + ":" + attempt.getDeadlineTime(), now, userId);
        }
        return attemptVO(attempt, version, false, now);
    }

    @Override
    @Transactional
    public HeartbeatVO heartbeat(Long attemptId, HeartbeatDTO request, String ipAddress) {
        long userId = currentUserId();
        validateSession(request == null ? null : request.getSessionId());
        ExamAttempt attempt = ownedAttemptForUpdate(attemptId, userId);
        LocalDateTime now = now();
        if (isExpired(attempt, now)) {
            finalizeInternal(attempt, ExamAttemptStatus.TIMED_OUT, "DEADLINE",
                    "timeout:" + attempt.getAttemptId() + ":" + attempt.getDeadlineTime(), now, userId);
        }
        boolean changed = !Objects.equals(attempt.getCurrentSessionId(), request.getSessionId());
        if (changed && !Boolean.TRUE.equals(request.getTakeover())
                && ExamAttemptStatus.fromCode(attempt.getStatus()) == ExamAttemptStatus.IN_PROGRESS) {
            throw new ServiceException(ResultCode.EXAM_SESSION_CONFLICT,
                    Map.of("requiresTakeover", true));
        }
        if (ExamAttemptStatus.fromCode(attempt.getStatus()) == ExamAttemptStatus.IN_PROGRESS) {
            attempt.setCurrentSessionId(request.getSessionId());
            attempt.setLatestIpHash(hashEvidence(ipAddress));
            attempt.setLastActiveTime(now);
            attempt.setUpdateTime(now);
            attempt.setRowVersion(attempt.getRowVersion() + 1);
            attemptMapper.updateById(attempt);
            if (changed) {
                audit(attempt.getExamId(), attemptId, userId, "SESSION_TAKEN_OVER",
                        request.getSessionId(), Map.of());
            }
        }
        HeartbeatVO result = new HeartbeatVO();
        result.setStatus(ExamAttemptStatus.fromCode(attempt.getStatus()).name());
        result.setServerNow(now);
        result.setDeadlineAt(attempt.getDeadlineTime());
        result.setSessionChanged(changed);
        return result;
    }

    @Override
    @Transactional(noRollbackFor = ExamAttemptExpiredException.class)
    public ExamAnswerVO saveAnswer(Long attemptId, Long versionQuestionId, SaveAnswerDTO request) {
        long userId = currentUserId();
        validateAnswerRequest(request);
        ExamAttempt attempt = ownedAttemptForUpdate(attemptId, userId);
        LocalDateTime now = now();
        requireWritableAttempt(attempt, now, userId);
        requireVersionQuestion(versionQuestionId, attempt.getVersionId());
        ExamAnswer answer = answerMapper.selectOne(new LambdaQueryWrapper<ExamAnswer>()
                .eq(ExamAnswer::getAttemptId, attemptId)
                .eq(ExamAnswer::getVersionQuestionId, versionQuestionId));
        int currentVersion = answer == null ? 0 : answer.getAnswerVersion();
        if (!Objects.equals(request.getExpectedVersion(), currentVersion)) {
            throw answerConflict(answer);
        }
        String hash = DigestUtil.sha256Hex(request.getContent());
        if (request.getContentHash() != null && !request.getContentHash().isBlank()
                && !hash.equals(stripHashPrefix(request.getContentHash()))) {
            throw new ServiceException(ResultCode.FAILED_PARAMS_VALIDATE,
                    Map.of("field", "contentHash", "rule", "matchesContent"));
        }
        if (answer == null) {
            answer = new ExamAnswer();
            answer.setAttemptId(attemptId);
            answer.setVersionQuestionId(versionQuestionId);
            answer.setCreateTime(now);
        }
        answer.setAnswerType(request.getAnswerType() == null ? "CODE" : request.getAnswerType());
        answer.setLanguageCode(request.getLanguage() == null ? "java" : request.getLanguage());
        answer.setAnswerContent(request.getContent());
        answer.setContentHash(hash);
        answer.setAnswerVersion(currentVersion + 1);
        answer.setSavedTime(now);
        answer.setUpdateTime(now);
        if (currentVersion == 0) {
            answerMapper.insert(answer);
        } else {
            answerMapper.updateById(answer);
        }
        attempt.setLastActiveTime(now);
        attempt.setUpdateTime(now);
        attemptMapper.updateById(attempt);
        audit(attempt.getExamId(), attemptId, userId, "ANSWER_SAVED", "save:" + answer.getAnswerId(),
                Map.of("versionQuestionId", versionQuestionId, "answerVersion", answer.getAnswerVersion()));
        return answerVO(answer);
    }

    @Override
    @Transactional(noRollbackFor = ExamAttemptExpiredException.class)
    public ExamSubmissionVO submit(Long attemptId, ExamSubmissionDTO request, String requestId) {
        long userId = currentUserId();
        validateKey(requestId, "Idempotency-Key");
        if (request == null || request.getVersionQuestionId() == null || request.getAnswerVersion() == null) {
            throw new ServiceException(ResultCode.FAILED_PARAMS_VALIDATE);
        }
        String kind = request.getSubmitKind() == null ? "FORMAL" : request.getSubmitKind().toUpperCase();
        if (!SUBMIT_KINDS.contains(kind)) {
            throw new ServiceException(ResultCode.FAILED_PARAMS_VALIDATE);
        }
        UserSubmit replay = userSubmitMapper.selectOne(new LambdaQueryWrapper<UserSubmit>()
                .eq(UserSubmit::getRequestId, requestId));
        if (replay != null) {
            if (!Objects.equals(replay.getUserId(), userId) || !Objects.equals(replay.getAttemptId(), attemptId)
                    || !Objects.equals(replay.getVersionQuestionId(), request.getVersionQuestionId())
                    || !Objects.equals(replay.getAnswerVersion(), request.getAnswerVersion())
                    || !Objects.equals(replay.getSubmitKind(), kind)) {
                throw new ServiceException(ResultCode.EXAM_IDEMPOTENCY_CONFLICT);
            }
            return submissionVO(replay, replayRemaining(replay), true);
        }
        ExamAttempt attempt = ownedAttemptForUpdate(attemptId, userId);
        LocalDateTime now = now();
        requireWritableAttempt(attempt, now, userId);
        ExamVersion version = getVersion(attempt.getVersionId());
        ExamVersionQuestion question = requireVersionQuestion(request.getVersionQuestionId(), attempt.getVersionId());
        ExamAnswer answer = answerMapper.selectOne(new LambdaQueryWrapper<ExamAnswer>()
                .eq(ExamAnswer::getAttemptId, attemptId)
                .eq(ExamAnswer::getVersionQuestionId, request.getVersionQuestionId()));
        if (answer == null) {
            throw new ServiceException(ResultCode.EXAM_ANSWER_NOT_FOUND);
        }
        if (!Objects.equals(answer.getAnswerVersion(), request.getAnswerVersion())) {
            throw answerConflict(answer);
        }
        if (!"java".equalsIgnoreCase(answer.getLanguageCode())) {
            throw new ServiceException(ResultCode.FAILED_NOT_SUPPORT_PROGRAM);
        }
        int priorFormal = formalSubmissionCount(attemptId, request.getVersionQuestionId());
        if ("FORMAL".equals(kind) && priorFormal >= version.getMaxFormalSubmissions()) {
            throw new ServiceException(ResultCode.EXAM_SUBMISSION_LIMIT_REACHED);
        }
        JudgeSubmitDTO payload = judgePayload(requestId, attempt, answer, question, kind);
        UserSubmit submission = acceptedSubmission(payload, attempt, answer, question, kind, now);
        userSubmitMapper.insert(submission);
        if ("FORMAL".equals(kind)) {
            answer.setLatestSubmitId(submission.getSubmitId());
            answer.setUpdateTime(now);
            answerMapper.updateById(answer);
        }
        audit(attempt.getExamId(), attemptId, userId, "ANSWER_SUBMITTED", requestId,
                Map.of("versionQuestionId", question.getVersionQuestionId(), "submitKind", kind,
                        "answerVersion", answer.getAnswerVersion()));
        publishAfterCommit(payload);
        int remaining = "FORMAL".equals(kind)
                ? version.getMaxFormalSubmissions() - priorFormal - 1
                : version.getMaxFormalSubmissions() - priorFormal;
        return submissionVO(submission, remaining, false);
    }

    @Override
    @Transactional
    public ExamFinalizeVO finalizeAttempt(Long attemptId, String idempotencyKey, String requestId) {
        long userId = currentUserId();
        validateKey(idempotencyKey, "Idempotency-Key");
        String requestHash = DigestUtil.sha256Hex("FINALIZE:" + attemptId);
        ExamCommand existingCommand = findCommand("FINALIZE", userId, idempotencyKey);
        if (existingCommand != null) {
            return replay(existingCommand, requestHash, ExamFinalizeVO.class, true);
        }
        ExamCommand command = beginCommand("FINALIZE", userId, idempotencyKey, requestHash, "ATTEMPT");
        ExamAttempt attempt = ownedAttemptForUpdate(attemptId, userId);
        LocalDateTime now = now();
        if (ExamAttemptStatus.fromCode(attempt.getStatus()) == ExamAttemptStatus.IN_PROGRESS) {
            ExamAttemptStatus target = isExpired(attempt, now)
                    ? ExamAttemptStatus.TIMED_OUT : ExamAttemptStatus.SUBMITTED;
            String reason = target == ExamAttemptStatus.TIMED_OUT ? "DEADLINE" : "CANDIDATE_SUBMIT";
            finalizeInternal(attempt, target, reason, idempotencyKey, now, userId);
        }
        ExamFinalizeVO result = finalizeVO(attempt, false);
        finishCommand(command, attemptId, result, now);
        audit(attempt.getExamId(), attemptId, userId, "ATTEMPT_FINALIZED",
                safeRequestId(requestId, idempotencyKey), Map.of("reason", attempt.getFinalizationReason()));
        return result;
    }

    @Override
    @Transactional
    public ExamFinalizeVO receipt(Long attemptId) {
        long userId = currentUserId();
        ExamAttempt attempt = ownedAttemptForUpdate(attemptId, userId);
        LocalDateTime now = now();
        if (isExpired(attempt, now)) {
            finalizeInternal(attempt, ExamAttemptStatus.TIMED_OUT, "DEADLINE",
                    "timeout:" + attempt.getAttemptId() + ":" + attempt.getDeadlineTime(), now, userId);
        }
        return finalizeVO(attempt, false);
    }

    @Override
    @Transactional(readOnly = true)
    public ExamResultVO result(Long attemptId) {
        long userId = currentUserId();
        ExamAttempt attempt = ownedAttemptForUpdate(attemptId, userId);
        Exam exam = examMapper.selectById(attempt.getExamId());
        if (exam == null || ExamStatus.fromCode(exam.getStatus()) != ExamStatus.RESULT_RELEASED) {
            throw new ServiceException(ResultCode.EXAM_RESULT_NOT_RELEASED);
        }
        ExamGrade grade = gradeMapper.selectOne(new LambdaQueryWrapper<ExamGrade>()
                .eq(ExamGrade::getAttemptId, attemptId)
                .eq(ExamGrade::getCurrentFlag, 1));
        if (grade == null || ExamGradeStatus.fromCode(grade.getStatus()) != ExamGradeStatus.RELEASED) {
            throw new ServiceException(ResultCode.EXAM_GRADE_NOT_READY);
        }
        ExamResultVO result = new ExamResultVO();
        result.setAttemptId(attemptId);
        result.setStatus(ExamGradeStatus.RELEASED.name());
        result.setTotalScore(grade.getTotalScore());
        result.setMaxScore(grade.getMaxScore());
        result.setReleasedAt(grade.getReleasedTime());
        result.setItems(gradeItemMapper.selectList(new LambdaQueryWrapper<ExamGradeItem>()
                        .eq(ExamGradeItem::getGradeId, grade.getGradeId())
                        .orderByAsc(ExamGradeItem::getVersionQuestionId))
                .stream().map(this::gradeItemVO).toList());
        return result;
    }

    @Override
    @Transactional
    public IntegrityBatchResultVO recordIntegrityEvents(Long attemptId, IntegrityEventBatchDTO request) {
        long userId = currentUserId();
        ExamAttempt attempt = ownedAttemptForUpdate(attemptId, userId);
        validateIntegrityBatch(attempt, request);
        LocalDateTime now = now();
        int accepted = 0;
        int duplicates = 0;
        int riskPoints = 0;
        for (IntegrityEventDTO item : request.getEvents()) {
            IntegrityEvent event = new IntegrityEvent();
            event.setAttemptId(attemptId);
            event.setSessionId(request.getSessionId());
            event.setClientSequence(item.getClientSequence());
            event.setEventType(item.getEventType());
            event.setClientObservedTime(item.getClientObservedTime());
            event.setServerReceivedTime(now);
            event.setMetadataJson(writeJson(safeIntegrityMetadata(item.getMetadata())));
            int points = integrityRiskPoints(item.getEventType());
            event.setRiskPoints(points);
            event.setCreateTime(now);
            try {
                integrityEventMapper.insert(event);
                accepted++;
                riskPoints += points;
            } catch (DuplicateKeyException exception) {
                duplicates++;
            }
        }
        if (accepted > 0) {
            Integer storedRiskPoints = integrityEventMapper.sumRiskPointsByAttemptId(attemptId);
            int cumulativeRiskPoints = storedRiskPoints == null ? riskPoints : storedRiskPoints;
            int calculatedLevel = cumulativeRiskPoints >= 10 ? 3 : cumulativeRiskPoints >= 5 ? 2
                    : cumulativeRiskPoints > 0 ? 1 : 0;
            attempt.setRiskLevel(calculatedLevel);
            attempt.setUpdateTime(now);
            attempt.setRowVersion(attempt.getRowVersion() + 1);
            attemptMapper.updateById(attempt);
            audit(attempt.getExamId(), attemptId, userId, "INTEGRITY_EVENTS_RECORDED",
                    "integrity:" + request.getSessionId() + ":" + request.getEvents().get(0).getClientSequence(),
                    Map.of("accepted", accepted, "duplicates", duplicates, "batchRiskPoints", riskPoints,
                            "cumulativeRiskPoints", cumulativeRiskPoints));
        }
        return new IntegrityBatchResultVO(accepted, duplicates, riskPoints);
    }

    private void reconcileExamState(Exam exam, LocalDateTime now) {
        ExamStatus state = ExamStatus.fromCode(exam.getStatus());
        ExamStatus target = state;
        if (state == ExamStatus.PUBLISHED && !now.isBefore(exam.getStartTime()) && now.isBefore(exam.getEndTime())) {
            target = ExamStatus.ACTIVE;
        } else if ((state == ExamStatus.PUBLISHED || state == ExamStatus.ACTIVE) && !now.isBefore(exam.getEndTime())) {
            target = ExamStatus.FINISHED;
        }
        if (target != state) {
            exam.setStatus(target.getCode());
            exam.setRowVersion(exam.getRowVersion() + 1);
            if (target == ExamStatus.FINISHED) {
                exam.setFinishedTime(now);
            }
            examMapper.updateById(exam);
        }
    }

    private ExamStatus effectiveStatus(Exam exam, ExamVersion version, LocalDateTime now) {
        ExamStatus stored = ExamStatus.fromCode(exam.getStatus());
        if (stored == ExamStatus.CANCELLED || stored == ExamStatus.RESULT_RELEASED) {
            return stored;
        }
        if (!now.isBefore(version.getEndTime())) {
            return ExamStatus.FINISHED;
        }
        if (!now.isBefore(version.getStartTime())) {
            return ExamStatus.ACTIVE;
        }
        return ExamStatus.PUBLISHED;
    }

    private void finalizeInternal(ExamAttempt attempt, ExamAttemptStatus target, String reason,
                                  String finalizationKey, LocalDateTime now, long actorId) {
        if (ExamAttemptStatus.fromCode(attempt.getStatus()) != ExamAttemptStatus.IN_PROGRESS) {
            return;
        }
        attempt.setStatus(target.getCode());
        attempt.setSubmittedTime(now);
        attempt.setFinalizedTime(now);
        attempt.setFinalizationReason(reason);
        attempt.setFinalizationKey(finalizationKey);
        attempt.setLastActiveTime(now);
        attempt.setUpdateTime(now);
        attempt.setRowVersion(attempt.getRowVersion() + 1);
        attemptMapper.updateById(attempt);
        answerMapper.update(null, new UpdateWrapper<ExamAnswer>()
                .eq("attempt_id", attempt.getAttemptId())
                .isNull("frozen_time")
                .set("frozen_time", now)
                .set("update_time", now));
        ensureGrade(attempt, now, actorId);
    }

    private void ensureGrade(ExamAttempt attempt, LocalDateTime now, long actorId) {
        Long count = gradeMapper.selectCount(new LambdaQueryWrapper<ExamGrade>()
                .eq(ExamGrade::getAttemptId, attempt.getAttemptId()));
        if (count != null && count > 0) {
            return;
        }
        List<ExamVersionQuestion> questions = versionQuestions(attempt.getVersionId());
        ExamGrade grade = new ExamGrade();
        grade.setAttemptId(attempt.getAttemptId());
        grade.setRevision(1);
        grade.setStatus(ExamGradeStatus.WAITING_FOR_JUDGE.getCode());
        grade.setTotalScore(0);
        grade.setMaxScore(questions.stream().mapToInt(ExamVersionQuestion::getScore).sum());
        grade.setCalculationSource("AUTO");
        grade.setCurrentFlag(1);
        grade.setCreateBy(actorId);
        grade.setCreateTime(now);
        gradeMapper.insert(grade);
    }

    private void requireWritableAttempt(ExamAttempt attempt, LocalDateTime now, long actorId) {
        if (ExamAttemptStatus.fromCode(attempt.getStatus()) != ExamAttemptStatus.IN_PROGRESS) {
            throw new ServiceException(ResultCode.EXAM_ATTEMPT_TERMINAL);
        }
        if (isExpired(attempt, now)) {
            finalizeInternal(attempt, ExamAttemptStatus.TIMED_OUT, "DEADLINE",
                    "timeout:" + attempt.getAttemptId() + ":" + attempt.getDeadlineTime(), now, actorId);
            throw new ExamAttemptExpiredException();
        }
    }

    private boolean isExpired(ExamAttempt attempt, LocalDateTime now) {
        return ExamAttemptStatus.fromCode(attempt.getStatus()) == ExamAttemptStatus.IN_PROGRESS
                && !now.isBefore(attempt.getDeadlineTime());
    }

    private Exam requirePublishedExam(Long examId) {
        Exam exam = examMapper.selectById(examId);
        if (exam == null) {
            throw new ServiceException(ResultCode.EXAM_NOT_EXISTS);
        }
        ExamStatus status = ExamStatus.fromCode(exam.getStatus());
        if (status == ExamStatus.CANCELLED) {
            throw new ServiceException(ResultCode.EXAM_CANCELLED);
        }
        if (status == ExamStatus.DRAFT || exam.getCurrentVersionId() == null) {
            throw new ServiceException(ResultCode.EXAM_NOT_PUBLISHED);
        }
        return exam;
    }

    private void requireAuthorizedCandidate(Long examId, long userId) {
        UserExam authorization = userExamMapper.selectOne(new LambdaQueryWrapper<UserExam>()
                .eq(UserExam::getExamId, examId)
                .eq(UserExam::getUserId, userId));
        if (authorization == null || !Objects.equals(authorization.getAuthorizationStatus(), 1)) {
            throw new ServiceException(ResultCode.EXAM_CANDIDATE_NOT_AUTHORIZED);
        }
    }

    private void requireEnabledUser(long userId) {
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw new ServiceException(ResultCode.FAILED_UNAUTHORIZED);
        }
        if (!Objects.equals(user.getStatus(), 1)) {
            throw new ServiceException(ResultCode.FAILED_USER_BANNED);
        }
    }

    private ExamAttempt ownedAttemptForUpdate(Long attemptId, long userId) {
        ExamAttempt attempt = attemptMapper.selectByIdForUpdate(attemptId);
        if (attempt == null || !Objects.equals(attempt.getUserId(), userId)) {
            throw new ServiceException(ResultCode.EXAM_ATTEMPT_NOT_FOUND);
        }
        return attempt;
    }

    private ExamAttempt findAttempt(Long versionId, long userId) {
        return attemptMapper.selectOne(new LambdaQueryWrapper<ExamAttempt>()
                .eq(ExamAttempt::getVersionId, versionId)
                .eq(ExamAttempt::getUserId, userId));
    }

    private ExamVersion getVersion(Long versionId) {
        ExamVersion version = examVersionMapper.selectById(versionId);
        if (version == null) {
            throw new ServiceException(ResultCode.EXAM_NOT_PUBLISHED);
        }
        return version;
    }

    private ExamVersionQuestion requireVersionQuestion(Long questionId, Long versionId) {
        ExamVersionQuestion question = versionQuestionMapper.selectById(questionId);
        if (question == null || !Objects.equals(question.getVersionId(), versionId)) {
            throw new ServiceException(ResultCode.EXAM_QUESTION_NOT_IN_VERSION);
        }
        return question;
    }

    private List<ExamVersionQuestion> versionQuestions(Long versionId) {
        return versionQuestionMapper.selectList(new LambdaQueryWrapper<ExamVersionQuestion>()
                .eq(ExamVersionQuestion::getVersionId, versionId)
                .orderByAsc(ExamVersionQuestion::getQuestionOrder));
    }

    private List<ExamAnswer> attemptAnswers(Long attemptId) {
        return answerMapper.selectList(new LambdaQueryWrapper<ExamAnswer>()
                .eq(ExamAnswer::getAttemptId, attemptId)
                .orderByAsc(ExamAnswer::getVersionQuestionId));
    }

    private ExamAttemptVO attemptVO(ExamAttempt attempt, ExamVersion version, boolean replayed,
                                    LocalDateTime serverNow) {
        ExamAttemptVO result = new ExamAttemptVO();
        result.setAttemptId(attempt.getAttemptId());
        result.setExamId(attempt.getExamId());
        result.setVersionId(attempt.getVersionId());
        result.setTitle(version.getTitle());
        result.setDescription(version.getDescription());
        result.setStatus(ExamAttemptStatus.fromCode(attempt.getStatus()).name());
        result.setServerNow(serverNow);
        result.setStartedAt(attempt.getStartedTime());
        result.setDeadlineAt(attempt.getDeadlineTime());
        result.setSubmittedAt(attempt.getSubmittedTime());
        result.setFinalizationReason(attempt.getFinalizationReason());
        result.setTimezone(version.getTimezone());
        result.setReplayed(replayed);
        result.setQuestions(versionQuestions(version.getVersionId()).stream().map(this::questionVO).toList());
        result.setAnswers(attemptAnswers(attempt.getAttemptId()).stream().map(this::answerVO).toList());
        return result;
    }

    private TrustedExamQuestionVO questionVO(ExamVersionQuestion question) {
        TrustedExamQuestionVO result = new TrustedExamQuestionVO();
        result.setVersionQuestionId(question.getVersionQuestionId());
        result.setQuestionOrder(question.getQuestionOrder());
        result.setScore(question.getScore());
        result.setRequired(Objects.equals(question.getRequiredFlag(), 1));
        result.setQuestionType(question.getQuestionType());
        result.setTitle(question.getTitle());
        result.setContent(question.getContent());
        result.setTimeLimit(question.getTimeLimit());
        result.setSpaceLimit(question.getSpaceLimit());
        result.setAllowedLanguages(readJson(question.getAllowedLanguagesJson(), new TypeReference<List<String>>() {}, List.of("java")));
        result.setStarterCode(readJson(question.getStarterCodeJson(), new TypeReference<Map<String, String>>() {}, Map.of()));
        return result;
    }

    private ExamAnswerVO answerVO(ExamAnswer answer) {
        ExamAnswerVO result = new ExamAnswerVO();
        result.setAnswerId(answer.getAnswerId());
        result.setVersionQuestionId(answer.getVersionQuestionId());
        result.setAnswerType(answer.getAnswerType());
        result.setLanguage(answer.getLanguageCode());
        result.setContent(answer.getAnswerContent());
        result.setContentHash(answer.getContentHash());
        result.setAnswerVersion(answer.getAnswerVersion());
        result.setSavedAt(answer.getSavedTime());
        result.setFrozen(answer.getFrozenTime() != null);
        return result;
    }

    private ExamGradeItemVO gradeItemVO(ExamGradeItem item) {
        ExamGradeItemVO result = new ExamGradeItemVO();
        result.setVersionQuestionId(item.getVersionQuestionId());
        result.setAwardedScore(item.getAwardedScore());
        result.setMaxScore(item.getMaxScore());
        result.setGradingMode(item.getGradingMode());
        return result;
    }

    private void validateIntegrityBatch(ExamAttempt attempt, IntegrityEventBatchDTO request) {
        if (ExamAttemptStatus.fromCode(attempt.getStatus()) != ExamAttemptStatus.IN_PROGRESS
                || request == null || request.getSessionId() == null
                || !Objects.equals(request.getSessionId(), attempt.getCurrentSessionId())
                || request.getEvents() == null || request.getEvents().isEmpty()
                || request.getEvents().size() > 100) {
            throw new ServiceException(ResultCode.EXAM_INTEGRITY_EVENT_REJECTED);
        }
        long previous = -1;
        for (IntegrityEventDTO item : request.getEvents()) {
            if (item == null || item.getClientSequence() == null || item.getClientSequence() < 0
                    || item.getClientSequence() <= previous || item.getEventType() == null
                    || !INTEGRITY_EVENT_TYPES.contains(item.getEventType())) {
                throw new ServiceException(ResultCode.EXAM_INTEGRITY_EVENT_REJECTED);
            }
            previous = item.getClientSequence();
        }
    }

    private Map<String, Object> safeIntegrityMetadata(Map<String, Object> metadata) {
        if (metadata == null || metadata.isEmpty()) {
            return Map.of();
        }
        Map<String, Object> safe = new java.util.LinkedHashMap<>();
        metadata.forEach((key, value) -> {
            if (INTEGRITY_METADATA_KEYS.contains(key)
                    && (value instanceof String || value instanceof Number || value instanceof Boolean)) {
                safe.put(key, value);
            }
        });
        return safe;
    }

    private int integrityRiskPoints(String eventType) {
        return switch (eventType) {
            case "FULLSCREEN_EXIT" -> 2;
            case "SESSION_CHANGE" -> 3;
            default -> 1;
        };
    }

    private ExamFinalizeVO finalizeVO(ExamAttempt attempt, boolean replayed) {
        ExamFinalizeVO result = new ExamFinalizeVO();
        result.setAttemptId(attempt.getAttemptId());
        result.setStatus(ExamAttemptStatus.fromCode(attempt.getStatus()).name());
        result.setFinalizationReason(attempt.getFinalizationReason());
        result.setSubmittedAt(attempt.getSubmittedTime());
        ExamGrade grade = gradeMapper.selectOne(new LambdaQueryWrapper<ExamGrade>()
                .eq(ExamGrade::getAttemptId, attempt.getAttemptId())
                .eq(ExamGrade::getCurrentFlag, 1));
        result.setGradeStatus(grade == null ? "PROCESSING" : ExamGradeStatus.fromCode(grade.getStatus()).name());
        result.setReplayed(replayed);
        return result;
    }

    private ServiceException answerConflict(ExamAnswer answer) {
        return new ServiceException(ResultCode.EXAM_ANSWER_VERSION_CONFLICT,
                Map.of("currentVersion", answer == null ? 0 : answer.getAnswerVersion(),
                        "currentHash", answer == null ? "" : answer.getContentHash()));
    }

    private void validateAnswerRequest(SaveAnswerDTO request) {
        if (request == null || request.getExpectedVersion() == null || request.getExpectedVersion() < 0
                || request.getContent() == null || request.getContent().length() > MAX_ANSWER_LENGTH) {
            throw new ServiceException(ResultCode.FAILED_PARAMS_VALIDATE);
        }
        String type = request.getAnswerType() == null ? "CODE" : request.getAnswerType();
        String language = request.getLanguage() == null ? "java" : request.getLanguage();
        if (!"CODE".equals(type) || !"java".equalsIgnoreCase(language)) {
            throw new ServiceException(ResultCode.FAILED_NOT_SUPPORT_PROGRAM);
        }
    }

    private int formalSubmissionCount(Long attemptId, Long versionQuestionId) {
        Long count = userSubmitMapper.selectCount(new LambdaQueryWrapper<UserSubmit>()
                .eq(UserSubmit::getAttemptId, attemptId)
                .eq(UserSubmit::getVersionQuestionId, versionQuestionId)
                .eq(UserSubmit::getSubmitKind, "FORMAL"));
        return count == null ? 0 : Math.toIntExact(count);
    }

    private int replayRemaining(UserSubmit submission) {
        ExamAttempt attempt = attemptMapper.selectById(submission.getAttemptId());
        if (attempt == null) {
            return 0;
        }
        ExamVersion version = getVersion(attempt.getVersionId());
        return Math.max(0, version.getMaxFormalSubmissions()
                - formalSubmissionCount(attempt.getAttemptId(), submission.getVersionQuestionId()));
    }

    private JudgeSubmitDTO judgePayload(String requestId, ExamAttempt attempt, ExamAnswer answer,
                                        ExamVersionQuestion question, String kind) {
        JudgeSubmitDTO payload = new JudgeSubmitDTO();
        payload.setRequestId(requestId);
        payload.setUserId(attempt.getUserId());
        payload.setExamId(attempt.getExamId());
        payload.setAttemptId(attempt.getAttemptId());
        payload.setVersionQuestionId(question.getVersionQuestionId());
        payload.setAnswerId(answer.getAnswerId());
        payload.setAnswerVersion(answer.getAnswerVersion());
        payload.setSubmitKind(kind);
        payload.setQuestionId(question.getQuestionId());
        payload.setProgramType(ProgramType.JAVA.getValue());
        payload.setDifficulty(1);
        payload.setTimeLimit(question.getTimeLimit());
        payload.setSpaceLimit(question.getSpaceLimit());
        payload.setUserCode(answer.getAnswerContent());
        List<String> inputs = new ArrayList<>();
        List<String> outputs = new ArrayList<>();
        try {
            JsonNode cases = objectMapper.readTree(question.getQuestionCase());
            for (JsonNode item : cases) {
                inputs.add(item.path("input").asText());
                outputs.add(item.path("output").asText());
            }
        } catch (JsonProcessingException exception) {
            throw new ServiceException(ResultCode.ERROR);
        }
        payload.setInputList(inputs);
        payload.setOutputList(outputs);
        return payload;
    }

    private UserSubmit acceptedSubmission(JudgeSubmitDTO payload, ExamAttempt attempt, ExamAnswer answer,
                                          ExamVersionQuestion question, String kind, LocalDateTime now) {
        UserSubmit submission = new UserSubmit();
        submission.setRequestId(payload.getRequestId());
        submission.setUserId(attempt.getUserId());
        submission.setQuestionId(question.getQuestionId());
        submission.setExamId(attempt.getExamId());
        submission.setAttemptId(attempt.getAttemptId());
        submission.setVersionQuestionId(question.getVersionQuestionId());
        submission.setAnswerId(answer.getAnswerId());
        submission.setAnswerVersion(answer.getAnswerVersion());
        submission.setSubmitKind(kind);
        submission.setProgramType(ProgramType.JAVA.getValue());
        submission.setUserCode(answer.getAnswerContent());
        submission.setPass(QuestionResType.IN_JUDGE.getValue());
        submission.setScore(0);
        submission.setExeMessage("判题中");
        submission.setJudgeStatus(JudgeAsyncStatus.WAITING.getValue());
        submission.setRetryCount(0);
        submission.setCreateBy(attempt.getUserId());
        submission.setCreateTime(now);
        return submission;
    }

    private ExamSubmissionVO submissionVO(UserSubmit submission, int remaining, boolean replayed) {
        ExamSubmissionVO result = new ExamSubmissionVO();
        result.setSubmitId(submission.getSubmitId());
        result.setRequestId(submission.getRequestId());
        result.setStatus("ACCEPTED");
        result.setSubmitKind(submission.getSubmitKind());
        result.setRemainingFormalSubmissions(Math.max(0, remaining));
        result.setReplayed(replayed);
        return result;
    }

    private void publishAfterCommit(JudgeSubmitDTO payload) {
        Runnable action = () -> {
            try {
                judgeRuntimeStateService.markAccepted(payload.getRequestId());
            } catch (RuntimeException exception) {
                log.warn("Could not record accepted judge state for {}", payload.getRequestId(), exception);
            }
            try {
                judgeProducer.produceMsg(payload);
            } catch (RuntimeException exception) {
                log.error("Trusted exam submission {} persisted but dispatch failed", payload.getRequestId(), exception);
            }
        };
        if (!TransactionSynchronizationManager.isSynchronizationActive()) {
            action.run();
            return;
        }
        TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
            @Override
            public void afterCommit() {
                action.run();
            }
        });
    }

    private ExamCommand beginCommand(String type, long actorId, String key, String requestHash,
                                     String targetType) {
        ExamCommand command = new ExamCommand();
        command.setCommandType(type);
        command.setActorId(actorId);
        command.setIdempotencyKey(key);
        command.setRequestHash(requestHash);
        command.setTargetType(targetType);
        command.setStatus(0);
        command.setExpiresTime(now().plusDays(180));
        command.setCreateTime(now());
        commandMapper.insert(command);
        return command;
    }

    private ExamCommand findCommand(String type, long actorId, String key) {
        return commandMapper.selectOne(new LambdaQueryWrapper<ExamCommand>()
                .eq(ExamCommand::getCommandType, type)
                .eq(ExamCommand::getActorId, actorId)
                .eq(ExamCommand::getIdempotencyKey, key));
    }

    private void finishCommand(ExamCommand command, Long targetId, Object response, LocalDateTime now) {
        command.setTargetId(targetId);
        command.setStatus(1);
        command.setResultCode(ResultCode.SUCCESS.getCode());
        command.setResponseJson(writeJson(response));
        command.setUpdateTime(now);
        commandMapper.updateById(command);
    }

    private <T> T replay(ExamCommand command, String requestHash, Class<T> type, boolean replayed) {
        if (!Objects.equals(command.getRequestHash(), requestHash)) {
            throw new ServiceException(ResultCode.EXAM_IDEMPOTENCY_CONFLICT);
        }
        if (Objects.equals(command.getStatus(), 0)) {
            throw new ServiceException(ResultCode.EXAM_COMMAND_IN_PROGRESS);
        }
        if (!Objects.equals(command.getStatus(), 1) || command.getResponseJson() == null) {
            throw new ServiceException(ResultCode.EXAM_STATE_CONFLICT);
        }
        try {
            T result = objectMapper.readValue(command.getResponseJson(), type);
            if (replayed && result instanceof ExamAttemptVO attempt) {
                attempt.setReplayed(true);
            } else if (replayed && result instanceof ExamFinalizeVO finalized) {
                finalized.setReplayed(true);
            }
            return result;
        } catch (JsonProcessingException exception) {
            throw new ServiceException(ResultCode.ERROR);
        }
    }

    private void audit(Long examId, Long attemptId, long actorId, String action, String requestId,
                       Map<String, Object> metadata) {
        ExamAuditEvent event = new ExamAuditEvent();
        event.setExamId(examId);
        event.setAttemptId(attemptId);
        event.setActorId(actorId);
        event.setActorType("CANDIDATE");
        event.setAction(action);
        event.setRequestId(safeRequestId(requestId, action));
        event.setResultCode(ResultCode.SUCCESS.getCode());
        event.setMetadataJson(writeJson(metadata));
        event.setServerTime(now());
        auditMapper.insert(event);
    }

    private <T> T readJson(String json, TypeReference<T> type, T fallback) {
        if (json == null || json.isBlank()) {
            return fallback;
        }
        try {
            return objectMapper.readValue(json, type);
        } catch (JsonProcessingException exception) {
            log.warn("Invalid trusted exam snapshot JSON", exception);
            return fallback;
        }
    }

    private String writeJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException exception) {
            throw new ServiceException(ResultCode.ERROR);
        }
    }

    private void validateSession(String sessionId) {
        validateKey(sessionId, "sessionId");
    }

    private void validateKey(String value, String field) {
        if (value == null || value.isBlank() || value.length() > 64
                || !value.chars().allMatch(character -> character >= 33 && character <= 126)) {
            throw new ServiceException(ResultCode.FAILED_PARAMS_VALIDATE,
                    Map.of("field", field, "rule", "asciiMax64"));
        }
    }

    private String stripHashPrefix(String hash) {
        return hash.startsWith("sha256:") ? hash.substring("sha256:".length()) : hash;
    }

    private String hashEvidence(String value) {
        return value == null || value.isBlank() ? null : DigestUtil.sha256Hex(evidenceSalt + ":" + value);
    }

    private String safeRequestId(String requestId, String fallback) {
        String value = requestId == null || requestId.isBlank() ? fallback : requestId;
        return value.substring(0, Math.min(64, value.length()));
    }

    private long currentUserId() {
        Long userId = ThreadLocalUtil.get(Constants.USER_ID, Long.class);
        if (userId == null) {
            throw new ServiceException(ResultCode.FAILED_UNAUTHORIZED);
        }
        return userId;
    }

    private LocalDateTime now() {
        return LocalDateTime.ofInstant(clock.instant(), ZoneOffset.UTC);
    }
}
