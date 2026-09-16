package com.sintao.system.service.exam.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sintao.common.core.constants.Constants;
import com.sintao.common.core.enums.ExamAttemptStatus;
import com.sintao.common.core.enums.ExamGradeStatus;
import com.sintao.common.core.enums.ExamStatus;
import com.sintao.common.core.enums.ResultCode;
import com.sintao.common.core.utils.ThreadLocalUtil;
import com.sintao.common.security.exception.ServiceException;
import com.sintao.system.domain.exam.Exam;
import com.sintao.system.domain.exam.ExamAnswer;
import com.sintao.system.domain.exam.ExamAttempt;
import com.sintao.system.domain.exam.ExamAuditEvent;
import com.sintao.system.domain.exam.ExamGrade;
import com.sintao.system.domain.exam.ExamGradeItem;
import com.sintao.system.domain.exam.ExamVersionQuestion;
import com.sintao.system.domain.exam.UserExam;
import com.sintao.system.domain.exam.IntegrityEvent;
import com.sintao.system.domain.exam.dto.CandidateAuthorizationDTO;
import com.sintao.system.domain.exam.dto.ExamGradeReviewDTO;
import com.sintao.system.domain.exam.vo.ExamCandidateVO;
import com.sintao.system.domain.exam.vo.ExamGradeVO;
import com.sintao.system.domain.exam.vo.ExamEvidenceEventVO;
import com.sintao.system.domain.exam.vo.ExamMonitorVO;
import com.sintao.system.domain.exam.vo.ExamGradeReviewVO;
import com.sintao.system.domain.user.User;
import com.sintao.system.mapper.exam.ExamAnswerMapper;
import com.sintao.system.mapper.exam.ExamAttemptMapper;
import com.sintao.system.mapper.exam.ExamAuditEventMapper;
import com.sintao.system.mapper.exam.ExamGradeMapper;
import com.sintao.system.mapper.exam.ExamGradeItemMapper;
import com.sintao.system.mapper.exam.ExamVersionQuestionMapper;
import com.sintao.system.mapper.exam.ExamMapper;
import com.sintao.system.mapper.exam.UserExamMapper;
import com.sintao.system.mapper.exam.IntegrityEventMapper;
import com.sintao.system.mapper.user.UserMapper;
import com.sintao.system.manager.ExamCacheManager;
import com.sintao.system.service.exam.IExamAdministrationService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

import java.time.Clock;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

@Service
public class ExamAdministrationServiceImpl implements IExamAdministrationService {

    private static final Logger log = LoggerFactory.getLogger(ExamAdministrationServiceImpl.class);
    private static final Set<String> AUTHORIZATION_SOURCES = Set.of("MANUAL", "IMPORT");

    private final ExamMapper examMapper;
    private final UserExamMapper userExamMapper;
    private final UserMapper userMapper;
    private final ExamAttemptMapper attemptMapper;
    private final ExamAnswerMapper answerMapper;
    private final ExamGradeMapper gradeMapper;
    private final ExamGradeItemMapper gradeItemMapper;
    private final ExamVersionQuestionMapper versionQuestionMapper;
    private final ExamAuditEventMapper auditMapper;
    private final IntegrityEventMapper integrityEventMapper;
    private final ExamCacheManager examCacheManager;
    private final ObjectMapper objectMapper;
    private final Clock clock;

    public ExamAdministrationServiceImpl(ExamMapper examMapper,
                                         UserExamMapper userExamMapper,
                                         UserMapper userMapper,
                                         ExamAttemptMapper attemptMapper,
                                         ExamAnswerMapper answerMapper,
                                         ExamGradeMapper gradeMapper,
                                         ExamGradeItemMapper gradeItemMapper,
                                         ExamVersionQuestionMapper versionQuestionMapper,
                                         ExamAuditEventMapper auditMapper,
                                         IntegrityEventMapper integrityEventMapper,
                                         ExamCacheManager examCacheManager,
                                         ObjectMapper objectMapper,
                                         Clock clock) {
        this.examMapper = examMapper;
        this.userExamMapper = userExamMapper;
        this.userMapper = userMapper;
        this.attemptMapper = attemptMapper;
        this.answerMapper = answerMapper;
        this.gradeMapper = gradeMapper;
        this.gradeItemMapper = gradeItemMapper;
        this.versionQuestionMapper = versionQuestionMapper;
        this.auditMapper = auditMapper;
        this.integrityEventMapper = integrityEventMapper;
        this.examCacheManager = examCacheManager;
        this.objectMapper = objectMapper;
        this.clock = clock;
    }

    @Override
    @Transactional
    public List<ExamCandidateVO> authorizeCandidates(Long examId, CandidateAuthorizationDTO request,
                                                      String requestId) {
        Exam exam = requireManageableExam(examId);
        if (request == null || request.getUserIds() == null || request.getUserIds().isEmpty()) {
            throw new ServiceException(ResultCode.FAILED_PARAMS_VALIDATE);
        }
        String source = request.getSource() == null ? "MANUAL" : request.getSource().toUpperCase();
        if (!AUTHORIZATION_SOURCES.contains(source)) {
            throw new ServiceException(ResultCode.FAILED_PARAMS_VALIDATE);
        }
        List<Long> userIds = new ArrayList<>(new LinkedHashSet<>(request.getUserIds()));
        List<User> users = userMapper.selectBatchIds(userIds);
        if (users.size() != userIds.size()) {
            throw new ServiceException(ResultCode.FAILED_USER_NOT_EXISTS);
        }
        LocalDateTime now = now();
        long actorId = currentActorId();
        for (Long userId : userIds) {
            UserExam relation = findAuthorization(examId, userId);
            if (relation == null) {
                relation = new UserExam();
                relation.setExamId(examId);
                relation.setUserId(userId);
                relation.setAuthorizationStatus(1);
                relation.setAuthorizationSource(source);
                relation.setCreateBy(actorId);
                relation.setCreateTime(now);
                userExamMapper.insert(relation);
            } else if (!Objects.equals(relation.getAuthorizationStatus(), 1)) {
                relation.setAuthorizationStatus(1);
                relation.setAuthorizationSource(source);
                relation.setRevokedBy(null);
                relation.setRevokedTime(null);
                relation.setRevokeReason(null);
                relation.setUpdateBy(actorId);
                relation.setUpdateTime(now);
                userExamMapper.updateById(relation);
            }
        }
        audit(exam.getExamId(), actorId, "CANDIDATES_AUTHORIZED", requestId,
                Map.of("userIds", userIds, "source", source));
        afterCommit(() -> userIds.forEach(examCacheManager::deleteUserExamList));
        return candidates(examId);
    }

    @Override
    @Transactional
    public void revokeCandidate(Long examId, Long userId, String reason, String requestId) {
        requireManageableExam(examId);
        if (reason == null || reason.isBlank() || reason.length() > 500) {
            throw new ServiceException(ResultCode.FAILED_PARAMS_VALIDATE);
        }
        Long attempts = attemptMapper.selectCount(new LambdaQueryWrapper<ExamAttempt>()
                .eq(ExamAttempt::getExamId, examId)
                .eq(ExamAttempt::getUserId, userId));
        if (attempts != null && attempts > 0) {
            throw new ServiceException(ResultCode.EXAM_STATE_CONFLICT,
                    Map.of("reason", "candidateAlreadyStarted"));
        }
        UserExam relation = findAuthorization(examId, userId);
        if (relation == null) {
            throw new ServiceException(ResultCode.EXAM_CANDIDATE_NOT_AUTHORIZED);
        }
        long actorId = currentActorId();
        relation.setAuthorizationStatus(0);
        relation.setRevokedBy(actorId);
        relation.setRevokedTime(now());
        relation.setRevokeReason(reason.trim());
        relation.setUpdateBy(actorId);
        relation.setUpdateTime(now());
        userExamMapper.updateById(relation);
        audit(examId, actorId, "CANDIDATE_REVOKED", requestId,
                Map.of("userId", userId, "reason", reason.trim()));
        afterCommit(() -> examCacheManager.deleteUserExamList(userId));
    }

    @Override
    public List<ExamCandidateVO> candidates(Long examId) {
        requireExam(examId);
        List<UserExam> authorizations = userExamMapper.selectList(new LambdaQueryWrapper<UserExam>()
                .eq(UserExam::getExamId, examId)
                .orderByAsc(UserExam::getCreateTime));
        if (authorizations.isEmpty()) {
            return List.of();
        }
        List<User> users = userMapper.selectBatchIds(authorizations.stream().map(UserExam::getUserId).toList());
        Map<Long, User> usersById = new HashMap<>();
        users.forEach(user -> usersById.put(user.getUserId(), user));
        List<ExamAttempt> attempts = attemptMapper.selectList(new LambdaQueryWrapper<ExamAttempt>()
                .eq(ExamAttempt::getExamId, examId));
        Map<Long, ExamAttempt> attemptsByUser = new HashMap<>();
        attempts.forEach(attempt -> attemptsByUser.put(attempt.getUserId(), attempt));
        return authorizations.stream()
                .map(item -> candidateVO(item, usersById.get(item.getUserId()), attemptsByUser.get(item.getUserId())))
                .toList();
    }

    @Override
    @Transactional
    public void cancel(Long examId, String reason, String requestId) {
        if (reason == null || reason.isBlank() || reason.length() > 500) {
            throw new ServiceException(ResultCode.FAILED_PARAMS_VALIDATE);
        }
        Exam exam = examMapper.selectByIdForUpdate(examId);
        if (exam == null) {
            throw new ServiceException(ResultCode.EXAM_NOT_EXISTS);
        }
        ExamStatus status = ExamStatus.fromCode(exam.getStatus());
        if (status == ExamStatus.CANCELLED) {
            return;
        }
        if (status != ExamStatus.PUBLISHED && status != ExamStatus.ACTIVE) {
            throw new ServiceException(ResultCode.EXAM_STATE_CONFLICT);
        }
        LocalDateTime now = now();
        exam.setStatus(ExamStatus.CANCELLED.getCode());
        exam.setCancelReason(reason.trim());
        exam.setRowVersion(exam.getRowVersion() + 1);
        examMapper.updateById(exam);

        List<ExamAttempt> active = attemptMapper.selectList(new LambdaQueryWrapper<ExamAttempt>()
                .eq(ExamAttempt::getExamId, examId)
                .eq(ExamAttempt::getStatus, ExamAttemptStatus.IN_PROGRESS.getCode()));
        for (ExamAttempt attempt : active) {
            attempt.setStatus(ExamAttemptStatus.CANCELLED.getCode());
            attempt.setSubmittedTime(now);
            attempt.setFinalizedTime(now);
            attempt.setFinalizationReason("EXAM_CANCEL");
            attempt.setFinalizationKey("exam-cancel:" + examId + ":" + attempt.getAttemptId());
            attempt.setUpdateTime(now);
            attempt.setRowVersion(attempt.getRowVersion() + 1);
            attemptMapper.updateById(attempt);
            answerMapper.update(null, new UpdateWrapper<ExamAnswer>()
                    .eq("attempt_id", attempt.getAttemptId())
                    .isNull("frozen_time")
                    .set("frozen_time", now)
                    .set("update_time", now));
        }
        audit(examId, currentActorId(), "EXAM_CANCELLED", requestId,
                Map.of("reason", reason.trim(), "cancelledAttempts", active.size()));
    }

    @Override
    public ExamMonitorVO monitor(Long examId) {
        Exam exam = requireExam(examId);
        List<ExamCandidateVO> candidates = candidates(examId);
        LocalDateTime disconnectedBefore = now().minusMinutes(2);
        ExamMonitorVO result = new ExamMonitorVO();
        result.setExamId(examId);
        result.setStatus(ExamStatus.fromCode(exam.getStatus()).name());
        result.setServerNow(now());
        result.setCandidates(candidates);
        result.setAuthorized((int) candidates.stream().filter(ExamCandidateVO::isAuthorized).count());
        result.setNotStarted((int) candidates.stream().filter(item -> item.isAuthorized() && item.getAttemptStatus() == null).count());
        result.setInProgress((int) candidates.stream().filter(item -> "IN_PROGRESS".equals(item.getAttemptStatus())).count());
        result.setDisconnected((int) candidates.stream().filter(item -> "IN_PROGRESS".equals(item.getAttemptStatus())
                && item.getLastActiveAt() != null && item.getLastActiveAt().isBefore(disconnectedBefore)).count());
        result.setSubmitted((int) candidates.stream().filter(item -> "SUBMITTED".equals(item.getAttemptStatus())).count());
        result.setTimedOut((int) candidates.stream().filter(item -> "TIMED_OUT".equals(item.getAttemptStatus())).count());
        result.setCancelled((int) candidates.stream().filter(item -> "CANCELLED".equals(item.getAttemptStatus())).count());
        return result;
    }

    @Override
    public List<ExamGradeVO> grades(Long examId) {
        requireExam(examId);
        List<ExamAttempt> attempts = attemptMapper.selectList(new LambdaQueryWrapper<ExamAttempt>()
                .eq(ExamAttempt::getExamId, examId)
                .orderByAsc(ExamAttempt::getStartedTime));
        if (attempts.isEmpty()) {
            return List.of();
        }
        Map<Long, ExamAttempt> attemptsById = new HashMap<>();
        attempts.forEach(attempt -> attemptsById.put(attempt.getAttemptId(), attempt));
        Map<Long, User> usersById = new HashMap<>();
        userMapper.selectBatchIds(attempts.stream().map(ExamAttempt::getUserId).distinct().toList())
                .forEach(user -> usersById.put(user.getUserId(), user));
        return gradeMapper.selectList(new LambdaQueryWrapper<ExamGrade>()
                        .in(ExamGrade::getAttemptId, attemptsById.keySet())
                        .eq(ExamGrade::getCurrentFlag, 1))
                .stream().map(grade -> gradeVO(grade, attemptsById.get(grade.getAttemptId()), usersById)).toList();
    }

    @Override
    @Transactional
    public void releaseResults(Long examId, String idempotencyKey, String requestId) {
        validateKey(idempotencyKey);
        Exam exam = examMapper.selectByIdForUpdate(examId);
        if (exam == null) {
            throw new ServiceException(ResultCode.EXAM_NOT_EXISTS);
        }
        ExamStatus status = ExamStatus.fromCode(exam.getStatus());
        if (status == ExamStatus.RESULT_RELEASED) {
            return;
        }
        if (status != ExamStatus.FINISHED || now().isBefore(exam.getEndTime())) {
            throw new ServiceException(ResultCode.EXAM_STATE_CONFLICT);
        }
        List<ExamAttempt> attempts = attemptMapper.selectList(new LambdaQueryWrapper<ExamAttempt>()
                .eq(ExamAttempt::getExamId, examId));
        if (attempts.isEmpty()) {
            throw new ServiceException(ResultCode.EXAM_GRADE_NOT_READY,
                    Map.of("reason", "noAttempts"));
        }
        List<ExamGrade> grades = gradeMapper.selectList(
                new LambdaQueryWrapper<ExamGrade>()
                        .in(ExamGrade::getAttemptId, attempts.stream().map(ExamAttempt::getAttemptId).toList())
                        .eq(ExamGrade::getCurrentFlag, 1));
        if (grades.size() != attempts.size() || grades.stream().anyMatch(grade ->
                ExamGradeStatus.fromCode(grade.getStatus()) != ExamGradeStatus.READY)) {
            throw new ServiceException(ResultCode.EXAM_GRADE_NOT_READY);
        }
        LocalDateTime now = now();
        for (ExamGrade grade : grades) {
            grade.setStatus(ExamGradeStatus.RELEASED.getCode());
            grade.setReleasedTime(now);
            grade.setUpdateTime(now);
            gradeMapper.updateById(grade);
        }
        exam.setStatus(ExamStatus.RESULT_RELEASED.getCode());
        exam.setResultReleasedTime(now);
        exam.setRowVersion(exam.getRowVersion() + 1);
        examMapper.updateById(exam);
        audit(examId, currentActorId(), "RESULTS_RELEASED", requestId,
                Map.of("gradeCount", grades.size(), "idempotencyKey", idempotencyKey));
    }

    @Override
    @Transactional(readOnly = true)
    public ExamGradeReviewVO grading(Long examId, Long attemptId) {
        requireExam(examId);
        ExamAttempt attempt = attemptMapper.selectById(attemptId);
        if (attempt == null || !Objects.equals(attempt.getExamId(), examId)) {
            throw new ServiceException(ResultCode.EXAM_ATTEMPT_NOT_FOUND);
        }
        ExamGrade grade = gradeMapper.selectOne(new LambdaQueryWrapper<ExamGrade>()
                .eq(ExamGrade::getAttemptId, attemptId)
                .eq(ExamGrade::getCurrentFlag, 1));
        if (grade == null) throw new ServiceException(ResultCode.EXAM_GRADE_NOT_READY);

        List<ExamVersionQuestion> questions = versionQuestionMapper.selectList(
                new LambdaQueryWrapper<ExamVersionQuestion>()
                        .eq(ExamVersionQuestion::getVersionId, attempt.getVersionId())
                        .orderByAsc(ExamVersionQuestion::getQuestionOrder));
        Map<Long, ExamAnswer> answers = new HashMap<>();
        answerMapper.selectList(new LambdaQueryWrapper<ExamAnswer>()
                        .eq(ExamAnswer::getAttemptId, attemptId))
                .forEach(answer -> answers.put(answer.getVersionQuestionId(), answer));
        Map<Long, ExamGradeItem> gradeItems = new HashMap<>();
        gradeItemMapper.selectList(new LambdaQueryWrapper<ExamGradeItem>()
                        .eq(ExamGradeItem::getGradeId, grade.getGradeId()))
                .forEach(item -> gradeItems.put(item.getVersionQuestionId(), item));

        ExamGradeReviewVO result = new ExamGradeReviewVO();
        result.setAttemptId(attemptId);
        User user = userMapper.selectById(attempt.getUserId());
        result.setCandidateName(user == null ? String.valueOf(attempt.getUserId())
                : (user.getNickName() == null ? user.getEmail() : user.getNickName()));
        result.setStatus(ExamGradeStatus.fromCode(grade.getStatus()).name());
        result.setTotalScore(grade.getTotalScore());
        result.setMaxScore(grade.getMaxScore());
        result.setItems(questions.stream().map(question -> reviewItem(question,
                answers.get(question.getVersionQuestionId()), gradeItems.get(question.getVersionQuestionId()))).toList());
        return result;
    }

    @Override
    @Transactional
    public ExamGradeReviewVO reviewGrade(Long examId, Long attemptId, ExamGradeReviewDTO request, String requestId) {
        requireExam(examId);
        ExamAttempt attempt = attemptMapper.selectById(attemptId);
        if (attempt == null || !Objects.equals(attempt.getExamId(), examId)
                || ExamAttemptStatus.fromCode(attempt.getStatus()) == ExamAttemptStatus.IN_PROGRESS) {
            throw new ServiceException(ResultCode.EXAM_ATTEMPT_NOT_FOUND);
        }
        ExamGrade grade = gradeMapper.selectOne(new LambdaQueryWrapper<ExamGrade>()
                .eq(ExamGrade::getAttemptId, attemptId).eq(ExamGrade::getCurrentFlag, 1));
        if (grade == null || ExamGradeStatus.fromCode(grade.getStatus()) == ExamGradeStatus.RELEASED) {
            throw new ServiceException(ResultCode.EXAM_STATE_CONFLICT);
        }
        List<ExamGradeItem> items = gradeItemMapper.selectList(new LambdaQueryWrapper<ExamGradeItem>()
                .eq(ExamGradeItem::getGradeId, grade.getGradeId()));
        Map<Long, ExamGradeReviewDTO.Item> submitted = new HashMap<>();
        if (request != null && request.getItems() != null) {
            request.getItems().forEach(item -> {
                if (item != null && item.getVersionQuestionId() != null) submitted.put(item.getVersionQuestionId(), item);
            });
        }
        LocalDateTime now = now();
        long actorId = currentActorId();
        for (ExamGradeItem item : items) {
            if (!"MANUAL".equals(item.getGradingMode())) continue;
            ExamGradeReviewDTO.Item reviewed = submitted.get(item.getVersionQuestionId());
            if (reviewed == null || reviewed.getAwardedScore() == null || reviewed.getAwardedScore() < 0
                    || reviewed.getAwardedScore() > item.getMaxScore()) {
                throw new ServiceException(ResultCode.FAILED_PARAMS_VALIDATE);
            }
            item.setAwardedScore(reviewed.getAwardedScore());
            item.setFeedback(trimTo(reviewed.getFeedback(), 1000));
            item.setAdjustmentReason("MANUAL_REVIEW");
            item.setUpdateBy(actorId);
            item.setUpdateTime(now);
            gradeItemMapper.updateById(item);
        }
        int total = items.stream().mapToInt(item -> item.getAwardedScore() == null ? 0 : item.getAwardedScore()).sum();
        grade.setTotalScore(total);
        grade.setStatus(ExamGradeStatus.READY.getCode());
        grade.setCalculationSource(items.stream().anyMatch(item -> "AUTO".equals(item.getGradingMode())) ? "MIXED" : "MANUAL");
        grade.setCalculatedTime(now);
        grade.setUpdateBy(actorId);
        grade.setUpdateTime(now);
        gradeMapper.updateById(grade);
        audit(examId, actorId, "GRADE_REVIEWED", requestId,
                Map.of("attemptId", attemptId, "totalScore", total, "maxScore", grade.getMaxScore()));
        return grading(examId, attemptId);
    }

    private ExamGradeReviewVO.Item reviewItem(ExamVersionQuestion question, ExamAnswer answer, ExamGradeItem gradeItem) {
        ExamGradeReviewVO.Item result = new ExamGradeReviewVO.Item();
        result.setVersionQuestionId(question.getVersionQuestionId());
        result.setQuestionOrder(question.getQuestionOrder());
        result.setTitle(question.getTitle());
        result.setQuestionType(question.getQuestionType());
        result.setMaxScore(question.getScore());
        result.setGradingRubric(gradingRubric(question.getGradingConfigJson()));
        if (answer != null) {
            result.setAnswerType(answer.getAnswerType());
            result.setLanguage(answer.getLanguageCode());
            result.setAnswerContent(answer.getAnswerContent());
        }
        if (gradeItem != null) {
            result.setAwardedScore(gradeItem.getAwardedScore());
            result.setGradingMode(gradeItem.getGradingMode());
            result.setFeedback(gradeItem.getFeedback());
        } else {
            result.setAwardedScore(0);
            result.setGradingMode("MANUAL");
        }
        return result;
    }

    private String gradingRubric(String gradingConfigJson) {
        if (gradingConfigJson == null || gradingConfigJson.isBlank()) return null;
        try {
            String rubric = objectMapper.readTree(gradingConfigJson).path("rubric").asText().trim();
            return rubric.isEmpty() ? null : rubric;
        } catch (Exception exception) {
            return null;
        }
    }

    private String trimTo(String value, int maxLength) {
        if (value == null) return null;
        return value.substring(0, Math.min(maxLength, value.length()));
    }

    @Override
    public List<ExamEvidenceEventVO> evidence(Long examId, Long attemptId) {
        requireExam(examId);
        ExamAttempt attempt = attemptMapper.selectById(attemptId);
        if (attempt == null || !Objects.equals(attempt.getExamId(), examId)) {
            throw new ServiceException(ResultCode.EXAM_ATTEMPT_NOT_FOUND);
        }
        List<ExamEvidenceEventVO> result = new ArrayList<>();
        integrityEventMapper.selectList(new LambdaQueryWrapper<IntegrityEvent>()
                        .eq(IntegrityEvent::getAttemptId, attemptId))
                .forEach(event -> {
                    ExamEvidenceEventVO item = new ExamEvidenceEventVO();
                    item.setCategory("INTEGRITY");
                    item.setEventType(event.getEventType());
                    item.setServerTime(event.getServerReceivedTime());
                    item.setClientObservedTime(event.getClientObservedTime());
                    item.setRiskPoints(event.getRiskPoints());
                    item.setMetadataJson(event.getMetadataJson());
                    result.add(item);
                });
        auditMapper.selectList(new LambdaQueryWrapper<ExamAuditEvent>()
                        .eq(ExamAuditEvent::getAttemptId, attemptId))
                .forEach(event -> {
                    ExamEvidenceEventVO item = new ExamEvidenceEventVO();
                    item.setCategory("AUDIT");
                    item.setEventType(event.getAction());
                    item.setServerTime(event.getServerTime());
                    item.setRiskPoints(0);
                    item.setMetadataJson(event.getMetadataJson());
                    result.add(item);
                });
        result.sort(java.util.Comparator.comparing(ExamEvidenceEventVO::getServerTime));
        return result;
    }

    private ExamCandidateVO candidateVO(UserExam relation, User user, ExamAttempt attempt) {
        ExamCandidateVO result = new ExamCandidateVO();
        result.setUserId(relation.getUserId());
        result.setNickName(user == null ? null : user.getNickName());
        result.setEmail(user == null ? null : user.getEmail());
        result.setAuthorized(Objects.equals(relation.getAuthorizationStatus(), 1));
        result.setAuthorizationSource(relation.getAuthorizationSource());
        if (attempt != null) {
            result.setAttemptId(attempt.getAttemptId());
            result.setAttemptStatus(ExamAttemptStatus.fromCode(attempt.getStatus()).name());
            result.setStartedAt(attempt.getStartedTime());
            result.setLastActiveAt(attempt.getLastActiveTime());
            result.setRiskLevel(attempt.getRiskLevel());
        }
        return result;
    }

    private ExamGradeVO gradeVO(ExamGrade grade, ExamAttempt attempt, Map<Long, User> usersById) {
        ExamGradeVO result = new ExamGradeVO();
        result.setGradeId(grade.getGradeId());
        result.setAttemptId(grade.getAttemptId());
        result.setUserId(attempt.getUserId());
        User user = usersById.get(attempt.getUserId());
        result.setNickName(user == null ? null : user.getNickName());
        result.setStatus(ExamGradeStatus.fromCode(grade.getStatus()).name());
        result.setTotalScore(grade.getTotalScore());
        result.setMaxScore(grade.getMaxScore());
        result.setRiskLevel(attempt.getRiskLevel());
        result.setCalculatedAt(grade.getCalculatedTime());
        result.setReleasedAt(grade.getReleasedTime());
        return result;
    }

    private Exam requireManageableExam(Long examId) {
        Exam exam = requireExam(examId);
        ExamStatus status = ExamStatus.fromCode(exam.getStatus());
        if (status != ExamStatus.DRAFT && status != ExamStatus.PUBLISHED && status != ExamStatus.ACTIVE) {
            throw new ServiceException(ResultCode.EXAM_STATE_CONFLICT);
        }
        return exam;
    }

    private Exam requireExam(Long examId) {
        Exam exam = examMapper.selectById(examId);
        if (exam == null) {
            throw new ServiceException(ResultCode.EXAM_NOT_EXISTS);
        }
        return exam;
    }

    private UserExam findAuthorization(Long examId, Long userId) {
        return userExamMapper.selectOne(new LambdaQueryWrapper<UserExam>()
                .eq(UserExam::getExamId, examId)
                .eq(UserExam::getUserId, userId));
    }

    private void audit(Long examId, long actorId, String action, String requestId, Map<String, Object> metadata) {
        ExamAuditEvent event = new ExamAuditEvent();
        event.setExamId(examId);
        event.setActorId(actorId);
        event.setActorType("ADMIN");
        event.setAction(action);
        event.setRequestId(safeRequestId(requestId, action));
        event.setResultCode(ResultCode.SUCCESS.getCode());
        event.setMetadataJson(writeJson(metadata));
        event.setServerTime(now());
        auditMapper.insert(event);
    }

    private String writeJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException exception) {
            throw new ServiceException(ResultCode.ERROR);
        }
    }

    private void validateKey(String key) {
        if (key == null || key.isBlank() || key.length() > 64) {
            throw new ServiceException(ResultCode.FAILED_PARAMS_VALIDATE);
        }
    }

    private String safeRequestId(String value, String fallback) {
        String result = value == null || value.isBlank() ? fallback : value;
        return result.substring(0, Math.min(64, result.length()));
    }

    private long currentActorId() {
        Long actorId = ThreadLocalUtil.get(Constants.USER_ID, Long.class);
        return actorId == null ? Constants.SYSTEM_USER_ID : actorId;
    }

    private LocalDateTime now() {
        return LocalDateTime.ofInstant(clock.instant(), ZoneOffset.UTC);
    }

    private void afterCommit(Runnable action) {
        if (!TransactionSynchronizationManager.isSynchronizationActive()) {
            runCacheAction(action);
            return;
        }
        TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
            @Override
            public void afterCommit() {
                runCacheAction(action);
            }
        });
    }

    private void runCacheAction(Runnable action) {
        try {
            action.run();
        } catch (RuntimeException exception) {
            log.warn("Exam administration transaction committed but cache invalidation failed", exception);
        }
    }
}
