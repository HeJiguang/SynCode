package com.sintao.system.service.exam.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.collection.CollectionUtil;
import cn.hutool.crypto.digest.DigestUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.github.pagehelper.PageHelper;
import com.sintao.common.core.constants.Constants;
import com.sintao.common.core.enums.ExamStatus;
import com.sintao.common.core.enums.ResultCode;
import com.sintao.common.core.utils.ThreadLocalUtil;
import com.sintao.common.security.exception.ServiceException;
import com.sintao.system.domain.exam.Exam;
import com.sintao.system.domain.exam.ExamAuditEvent;
import com.sintao.system.domain.exam.ExamCommand;
import com.sintao.system.domain.exam.ExamQuestion;
import com.sintao.system.domain.exam.ExamVersion;
import com.sintao.system.domain.exam.ExamVersionQuestion;
import com.sintao.system.domain.exam.dto.ExamAddDTO;
import com.sintao.system.domain.exam.dto.ExamEditDTO;
import com.sintao.system.domain.exam.dto.ExamQueryDTO;
import com.sintao.system.domain.exam.dto.ExamQuestAddDTO;
import com.sintao.system.domain.exam.dto.ExamQuestionItemDTO;
import com.sintao.system.domain.exam.dto.ExamQuestionsReplaceDTO;
import com.sintao.system.domain.exam.vo.ExamDetailVO;
import com.sintao.system.domain.exam.vo.ExamPublicationVO;
import com.sintao.system.domain.exam.vo.ExamVO;
import com.sintao.system.domain.exam.vo.ValidationViolationVO;
import com.sintao.system.domain.question.Question;
import com.sintao.system.domain.question.vo.QuestionVO;
import com.sintao.system.manager.ExamCacheManager;
import com.sintao.system.mapper.exam.ExamAuditEventMapper;
import com.sintao.system.mapper.exam.ExamCommandMapper;
import com.sintao.system.mapper.exam.ExamMapper;
import com.sintao.system.mapper.exam.ExamQuestionMapper;
import com.sintao.system.mapper.exam.ExamVersionMapper;
import com.sintao.system.mapper.exam.ExamVersionQuestionMapper;
import com.sintao.system.mapper.question.QuestionMapper;
import com.sintao.system.service.exam.IExamService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

import java.time.Clock;
import java.time.Duration;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

@Service
@Slf4j
public class ExamServiceImpl extends ServiceImpl<ExamQuestionMapper, ExamQuestion> implements IExamService {

    private static final String DEFAULT_TIMEZONE = "Asia/Shanghai";
    private static final String DEFAULT_RESULT_POLICY = "MANUAL";
    private static final String PROGRAMMING = "PROGRAMMING";
    private static final String JAVA_LANGUAGES_JSON = "[\"java\"]";

    private final ExamMapper examMapper;
    private final QuestionMapper questionMapper;
    private final ExamQuestionMapper examQuestionMapper;
    private final ExamVersionMapper examVersionMapper;
    private final ExamVersionQuestionMapper examVersionQuestionMapper;
    private final ExamCommandMapper examCommandMapper;
    private final ExamAuditEventMapper examAuditEventMapper;
    private final ExamCacheManager examCacheManager;
    private final ObjectMapper objectMapper;
    private final Clock clock;

    public ExamServiceImpl(ExamMapper examMapper,
                           QuestionMapper questionMapper,
                           ExamQuestionMapper examQuestionMapper,
                           ExamVersionMapper examVersionMapper,
                           ExamVersionQuestionMapper examVersionQuestionMapper,
                           ExamCommandMapper examCommandMapper,
                           ExamAuditEventMapper examAuditEventMapper,
                           ExamCacheManager examCacheManager,
                           ObjectMapper objectMapper,
                           Clock clock) {
        this.examMapper = examMapper;
        this.questionMapper = questionMapper;
        this.examQuestionMapper = examQuestionMapper;
        this.examVersionMapper = examVersionMapper;
        this.examVersionQuestionMapper = examVersionQuestionMapper;
        this.examCommandMapper = examCommandMapper;
        this.examAuditEventMapper = examAuditEventMapper;
        this.examCacheManager = examCacheManager;
        this.objectMapper = objectMapper;
        this.clock = clock;
    }

    @Override
    public List<ExamVO> list(ExamQueryDTO request) {
        PageHelper.startPage(request.getPageNum(), request.getPageSize());
        return examMapper.selectExamList(request);
    }

    @Override
    public String add(ExamAddDTO request) {
        normalizeRules(request);
        checkExamSaveParams(request, null);
        Exam exam = new Exam();
        BeanUtil.copyProperties(request, exam);
        exam.setStatus(ExamStatus.DRAFT.getCode());
        exam.setVersionNo(0);
        exam.setRowVersion(0);
        examMapper.insert(exam);
        return exam.getExamId().toString();
    }

    @Override
    @Transactional
    public boolean questionAdd(ExamQuestAddDTO request) {
        Exam exam = getExam(request.getExamId());
        requireDraft(exam);
        Set<Long> questionIds = request.getQuestionIdSet();
        if (CollectionUtil.isEmpty(questionIds)) {
            return true;
        }
        List<Question> questions = questionMapper.selectBatchIds(questionIds);
        if (CollectionUtil.isEmpty(questions) || questions.size() < questionIds.size()) {
            throw new ServiceException(ResultCode.EXAM_QUESTION_NOT_EXISTS);
        }
        return saveLegacyExamQuestions(exam, questionIds);
    }

    @Override
    @Transactional
    public boolean replaceQuestions(Long examId, ExamQuestionsReplaceDTO request) {
        requireDraft(getExam(examId));
        List<ExamQuestionItemDTO> items = request == null ? null : request.getQuestions();
        List<ValidationViolationVO> violations = validateComposition(items);
        if (!violations.isEmpty()) {
            throw validationException(violations);
        }
        Set<Long> questionIds = new HashSet<>();
        for (ExamQuestionItemDTO item : items) {
            questionIds.add(item.getQuestionId());
        }
        List<Question> questions = questionMapper.selectBatchIds(questionIds);
        if (questions.size() != questionIds.size()) {
            throw validationException(List.of(new ValidationViolationVO(
                    "questions", "exists", "组卷中包含不存在的题目")));
        }
        examQuestionMapper.delete(new LambdaQueryWrapper<ExamQuestion>()
                .eq(ExamQuestion::getExamId, examId));
        for (ExamQuestionItemDTO item : items) {
            ExamQuestion relation = new ExamQuestion();
            relation.setExamId(examId);
            relation.setQuestionId(item.getQuestionId());
            relation.setQuestionOrder(item.getQuestionOrder());
            relation.setScore(item.getScore());
            relation.setRequiredFlag(Boolean.FALSE.equals(item.getRequired()) ? 0 : 1);
            relation.setQuestionType(PROGRAMMING);
            examQuestionMapper.insert(relation);
        }
        return true;
    }

    @Override
    @Transactional
    public int questionDelete(Long examId, Long questionId) {
        requireDraft(getExam(examId));
        return examQuestionMapper.delete(new LambdaQueryWrapper<ExamQuestion>()
                .eq(ExamQuestion::getExamId, examId)
                .eq(ExamQuestion::getQuestionId, questionId));
    }

    @Override
    public ExamDetailVO detail(Long examId) {
        ExamDetailVO result = new ExamDetailVO();
        Exam exam = getExam(examId);
        BeanUtil.copyProperties(exam, result);
        List<QuestionVO> questions = examQuestionMapper.selectExamQuestionList(examId);
        if (CollectionUtil.isNotEmpty(questions)) {
            result.setExamQuestionList(questions);
        }
        result.setAllowedActions(allowedActions(exam));
        return result;
    }

    @Override
    @Transactional
    public int edit(ExamEditDTO request) {
        Exam exam = getExam(request.getExamId());
        requireDraft(exam);
        normalizeRules(request);
        checkExamSaveParams(request, request.getExamId());
        int expectedVersion = request.getExpectedRowVersion() == null
                ? exam.getRowVersion() : request.getExpectedRowVersion();
        Exam update = new Exam();
        BeanUtil.copyProperties(request, update);
        update.setExamId(exam.getExamId());
        update.setRowVersion(expectedVersion + 1);
        int rows = examMapper.update(update, new LambdaUpdateWrapper<Exam>()
                .eq(Exam::getExamId, exam.getExamId())
                .eq(Exam::getStatus, ExamStatus.DRAFT.getCode())
                .eq(Exam::getRowVersion, expectedVersion));
        if (rows == 0) {
            throw new ServiceException(ResultCode.EXAM_STATE_CONFLICT);
        }
        return rows;
    }

    @Override
    @Transactional
    public int delete(Long examId) {
        requireDraft(getExam(examId));
        examQuestionMapper.delete(new LambdaQueryWrapper<ExamQuestion>()
                .eq(ExamQuestion::getExamId, examId));
        return examMapper.deleteById(examId);
    }

    @Override
    public int publish(Long examId) {
        publish(examId, "legacy-" + UUID.randomUUID(), "legacy-publish");
        return 1;
    }

    @Override
    @Transactional
    public ExamPublicationVO publish(Long examId, String idempotencyKey, String requestId) {
        validateIdempotencyKey(idempotencyKey);
        long actorId = currentActorId();
        String requestHash = DigestUtil.sha256Hex("PUBLISH:" + examId);
        ExamCommand existing = findCommand("PUBLISH", actorId, idempotencyKey);
        if (existing != null) {
            return replayPublication(existing, requestHash);
        }

        LocalDateTime now = now();
        ExamCommand command = new ExamCommand();
        command.setCommandType("PUBLISH");
        command.setActorId(actorId);
        command.setIdempotencyKey(idempotencyKey);
        command.setRequestHash(requestHash);
        command.setTargetType("EXAM_VERSION");
        command.setStatus(0);
        command.setExpiresTime(now.plusDays(180));
        command.setCreateTime(now);
        examCommandMapper.insert(command);

        Exam exam = examMapper.selectByIdForUpdate(examId);
        if (exam == null) {
            throw new ServiceException(ResultCode.EXAM_NOT_EXISTS);
        }
        requireDraft(exam);
        List<ExamQuestion> relations = examQuestionMapper.selectList(
                new LambdaQueryWrapper<ExamQuestion>()
                        .eq(ExamQuestion::getExamId, examId)
                        .orderByAsc(ExamQuestion::getQuestionOrder));
        List<Question> questions = loadQuestions(relations);
        List<ValidationViolationVO> violations = validateForPublication(exam, relations, questions, now);
        if (!violations.isEmpty()) {
            throw validationException(violations);
        }

        Map<Long, Question> questionsById = new HashMap<>();
        for (Question question : questions) {
            questionsById.put(question.getQuestionId(), question);
        }
        List<ExamVersionQuestion> snapshots = new ArrayList<>();
        for (ExamQuestion relation : relations) {
            snapshots.add(snapshotQuestion(relation, questionsById.get(relation.getQuestionId())));
        }

        int versionNo = exam.getVersionNo() + 1;
        ExamVersion version = snapshotExam(exam, versionNo, actorId, now, snapshots);
        examVersionMapper.insert(version);
        for (ExamVersionQuestion snapshot : snapshots) {
            snapshot.setVersionId(version.getVersionId());
            examVersionQuestionMapper.insert(snapshot);
        }

        exam.setCurrentVersionId(version.getVersionId());
        exam.setVersionNo(versionNo);
        exam.setStatus(ExamStatus.PUBLISHED.getCode());
        exam.setPublishedTime(now);
        exam.setRowVersion(exam.getRowVersion() + 1);
        if (examMapper.updateById(exam) != 1) {
            throw new ServiceException(ResultCode.EXAM_STATE_CONFLICT);
        }

        ExamPublicationVO result = publicationVO(version, false);
        command.setTargetId(version.getVersionId());
        command.setStatus(1);
        command.setResultCode(ResultCode.SUCCESS.getCode());
        command.setResponseJson(writeJson(result));
        command.setUpdateTime(now);
        examCommandMapper.updateById(command);
        insertAudit(examId, actorId, "EXAM_PUBLISHED", safeRequestId(requestId, idempotencyKey),
                Map.of("versionId", version.getVersionId(), "versionNo", versionNo));
        afterCommit(() -> examCacheManager.addCache(exam));
        return result;
    }

    @Override
    @Transactional
    public int cancelPublish(Long examId) {
        Exam exam = examMapper.selectByIdForUpdate(examId);
        if (exam == null) {
            throw new ServiceException(ResultCode.EXAM_NOT_EXISTS);
        }
        if (ExamStatus.fromCode(exam.getStatus()) != ExamStatus.PUBLISHED || !now().isBefore(exam.getStartTime())) {
            throw new ServiceException(ResultCode.EXAM_STATE_CONFLICT);
        }
        exam.setStatus(ExamStatus.DRAFT.getCode());
        exam.setRowVersion(exam.getRowVersion() + 1);
        int rows = examMapper.updateById(exam);
        insertAudit(examId, currentActorId(), "EXAM_WITHDRAWN", "legacy-withdraw", Map.of());
        afterCommit(() -> examCacheManager.deleteCache(examId));
        return rows;
    }

    private void normalizeRules(ExamAddDTO request) {
        if (request == null) {
            throw new ServiceException(ResultCode.FAILED_PARAMS_VALIDATE);
        }
        if (request.getLatestStartTime() == null) {
            request.setLatestStartTime(request.getEndTime());
        }
        if (request.getDurationMinutes() == null && request.getStartTime() != null && request.getEndTime() != null) {
            request.setDurationMinutes((int) Math.max(1, Duration.between(
                    request.getStartTime(), request.getEndTime()).toMinutes()));
        }
        if (request.getTimezone() == null || request.getTimezone().isBlank()) {
            request.setTimezone(DEFAULT_TIMEZONE);
        }
        if (request.getMaxFormalSubmissions() == null) {
            request.setMaxFormalSubmissions(50);
        }
        if (request.getResultReleasePolicy() == null || request.getResultReleasePolicy().isBlank()) {
            request.setResultReleasePolicy(DEFAULT_RESULT_POLICY);
        }
    }

    private void checkExamSaveParams(ExamAddDTO request, Long examId) {
        List<ValidationViolationVO> violations = validateRules(request, now(), true);
        if (!violations.isEmpty()) {
            throw new ServiceException(ResultCode.FAILED_PARAMS_VALIDATE, Map.of("violations", violations));
        }
        List<Exam> duplicates = examMapper.selectList(new LambdaQueryWrapper<Exam>()
                .eq(Exam::getTitle, request.getTitle())
                .ne(examId != null, Exam::getExamId, examId));
        if (CollectionUtil.isNotEmpty(duplicates)) {
            throw new ServiceException(ResultCode.FAILED_ALREADY_EXISTS);
        }
    }

    private List<ValidationViolationVO> validateRules(ExamAddDTO request, LocalDateTime now,
                                                       boolean requireFutureStart) {
        List<ValidationViolationVO> violations = new ArrayList<>();
        if (request.getTitle() == null || request.getTitle().isBlank()) {
            violations.add(new ValidationViolationVO("title", "required", "考试标题不能为空"));
        }
        if (request.getStartTime() == null) {
            violations.add(new ValidationViolationVO("startTime", "required", "考试开始时间不能为空"));
        }
        if (request.getLatestStartTime() == null) {
            violations.add(new ValidationViolationVO("latestStartTime", "required", "最晚入场时间不能为空"));
        }
        if (request.getEndTime() == null) {
            violations.add(new ValidationViolationVO("endTime", "required", "考试结束时间不能为空"));
        }
        if (request.getStartTime() != null && requireFutureStart && !request.getStartTime().isAfter(now)) {
            violations.add(new ValidationViolationVO("startTime", "future", "考试开始时间必须晚于当前时间"));
        }
        if (request.getStartTime() != null && request.getLatestStartTime() != null
                && !request.getLatestStartTime().isAfter(request.getStartTime())) {
            violations.add(new ValidationViolationVO("latestStartTime", "afterStart", "最晚入场时间必须晚于开始时间"));
        }
        if (request.getLatestStartTime() != null && request.getEndTime() != null
                && request.getLatestStartTime().isAfter(request.getEndTime())) {
            violations.add(new ValidationViolationVO("latestStartTime", "beforeEnd", "最晚入场时间不能晚于结束时间"));
        }
        if (request.getStartTime() != null && request.getEndTime() != null
                && !request.getEndTime().isAfter(request.getStartTime())) {
            violations.add(new ValidationViolationVO("endTime", "afterStart", "考试结束时间必须晚于开始时间"));
        }
        if (request.getDurationMinutes() == null || request.getDurationMinutes() <= 0) {
            violations.add(new ValidationViolationVO("durationMinutes", "positive", "考试时长必须大于 0"));
        }
        if (request.getMaxFormalSubmissions() == null || request.getMaxFormalSubmissions() <= 0) {
            violations.add(new ValidationViolationVO("maxFormalSubmissions", "positive", "正式提交次数必须大于 0"));
        }
        try {
            ZoneId.of(request.getTimezone());
        } catch (RuntimeException exception) {
            violations.add(new ValidationViolationVO("timezone", "validZone", "时区标识无效"));
        }
        if (!Set.of("MANUAL", "SCHEDULED").contains(request.getResultReleasePolicy())) {
            violations.add(new ValidationViolationVO("resultReleasePolicy", "supported", "成绩发布策略无效"));
        }
        if ("SCHEDULED".equals(request.getResultReleasePolicy())
                && (request.getResultReleaseTime() == null || request.getEndTime() == null
                || request.getResultReleaseTime().isBefore(request.getEndTime()))) {
            violations.add(new ValidationViolationVO("resultReleaseTime", "notBeforeEnd", "定时发布成绩不能早于考试结束"));
        }
        return violations;
    }

    private List<ValidationViolationVO> validateComposition(List<ExamQuestionItemDTO> items) {
        List<ValidationViolationVO> violations = new ArrayList<>();
        if (items == null || items.isEmpty()) {
            violations.add(new ValidationViolationVO("questions", "notEmpty", "试卷至少包含一道题目"));
            return violations;
        }
        Set<Long> ids = new HashSet<>();
        Set<Integer> orders = new HashSet<>();
        for (int index = 0; index < items.size(); index++) {
            ExamQuestionItemDTO item = items.get(index);
            String prefix = "questions[" + index + "]";
            if (item == null || item.getQuestionId() == null) {
                violations.add(new ValidationViolationVO(prefix + ".questionId", "required", "题目不能为空"));
                continue;
            }
            if (!ids.add(item.getQuestionId())) {
                violations.add(new ValidationViolationVO(prefix + ".questionId", "unique", "同一题目不能重复添加"));
            }
            if (item.getQuestionOrder() == null || item.getQuestionOrder() <= 0) {
                violations.add(new ValidationViolationVO(prefix + ".questionOrder", "positive", "题序必须大于 0"));
            } else if (!orders.add(item.getQuestionOrder())) {
                violations.add(new ValidationViolationVO(prefix + ".questionOrder", "unique", "题序不能重复"));
            }
            if (item.getScore() == null || item.getScore() <= 0) {
                violations.add(new ValidationViolationVO(prefix + ".score", "positive", "题目分值必须大于 0"));
            }
            if (item.getQuestionType() != null && !PROGRAMMING.equals(item.getQuestionType())) {
                violations.add(new ValidationViolationVO(prefix + ".questionType", "supported", "第一阶段仅支持编程题"));
            }
        }
        for (int order = 1; order <= items.size(); order++) {
            if (!orders.contains(order)) {
                violations.add(new ValidationViolationVO("questions", "contiguousOrder", "题序必须从 1 连续排列"));
                break;
            }
        }
        return violations;
    }

    private List<ValidationViolationVO> validateForPublication(Exam exam, List<ExamQuestion> relations,
                                                                List<Question> questions, LocalDateTime now) {
        ExamAddDTO rules = new ExamAddDTO();
        BeanUtil.copyProperties(exam, rules);
        List<ValidationViolationVO> violations = validateRules(rules, now, true);
        if (relations.isEmpty()) {
            violations.add(new ValidationViolationVO("questions", "notEmpty", "试卷至少包含一道题目"));
            return violations;
        }
        if (questions.size() != relations.size()) {
            violations.add(new ValidationViolationVO("questions", "exists", "组卷中包含已删除的题目"));
        }
        Set<Integer> orders = new HashSet<>();
        Map<Long, Question> byId = new HashMap<>();
        for (Question question : questions) {
            byId.put(question.getQuestionId(), question);
        }
        for (int index = 0; index < relations.size(); index++) {
            ExamQuestion relation = relations.get(index);
            String prefix = "questions[" + index + "]";
            if (relation.getScore() == null || relation.getScore() <= 0) {
                violations.add(new ValidationViolationVO(prefix + ".score", "positive", "题目分值必须大于 0"));
            }
            if (relation.getQuestionOrder() == null || relation.getQuestionOrder() <= 0
                    || !orders.add(relation.getQuestionOrder())) {
                violations.add(new ValidationViolationVO(prefix + ".questionOrder", "uniquePositive", "题序必须为不重复的正整数"));
            }
            Question question = byId.get(relation.getQuestionId());
            if (question == null) {
                continue;
            }
            if (question.getTitle() == null || question.getTitle().isBlank()
                    || question.getContent() == null || question.getContent().isBlank()) {
                violations.add(new ValidationViolationVO(prefix, "completeStatement", "题目缺少标题或题面"));
            }
            if (question.getTimeLimit() == null || question.getTimeLimit() <= 0
                    || question.getSpaceLimit() == null || question.getSpaceLimit() <= 0) {
                violations.add(new ValidationViolationVO(prefix, "positiveLimits", "题目时间或内存限制无效"));
            }
            if (!isJsonArray(question.getQuestionCase())) {
                violations.add(new ValidationViolationVO(prefix + ".judgeCases", "validNonEmptyJson", "题目缺少有效测试数据"));
            }
        }
        for (int order = 1; order <= relations.size(); order++) {
            if (!orders.contains(order)) {
                violations.add(new ValidationViolationVO("questions", "contiguousOrder", "题序必须从 1 连续排列"));
                break;
            }
        }
        return violations;
    }

    private ExamVersionQuestion snapshotQuestion(ExamQuestion relation, Question question) {
        ExamVersionQuestion snapshot = new ExamVersionQuestion();
        snapshot.setQuestionId(question.getQuestionId());
        snapshot.setQuestionOrder(relation.getQuestionOrder());
        snapshot.setScore(relation.getScore());
        snapshot.setRequiredFlag(relation.getRequiredFlag());
        snapshot.setQuestionType(PROGRAMMING);
        snapshot.setTitle(question.getTitle());
        snapshot.setContent(question.getContent());
        snapshot.setTimeLimit(question.getTimeLimit());
        snapshot.setSpaceLimit(question.getSpaceLimit());
        snapshot.setQuestionCase(question.getQuestionCase());
        snapshot.setDefaultCode(question.getDefaultCode());
        snapshot.setMainFuc(question.getMainFuc());
        snapshot.setAllowedLanguagesJson(JAVA_LANGUAGES_JSON);
        snapshot.setStarterCodeJson(writeJson(Map.of("java", nullToEmpty(question.getDefaultCode()))));
        snapshot.setJudgeConfigJson(writeJson(Map.of("mode", "STANDARD")));
        snapshot.setSourceUpdateTime(question.getUpdateTime());
        snapshot.setContentHash(hashQuestion(snapshot));
        return snapshot;
    }

    private ExamVersion snapshotExam(Exam exam, int versionNo, long actorId, LocalDateTime now,
                                     List<ExamVersionQuestion> questions) {
        ExamVersion version = new ExamVersion();
        version.setExamId(exam.getExamId());
        version.setVersionNo(versionNo);
        version.setTitle(exam.getTitle());
        version.setDescription(exam.getDescription());
        version.setStartTime(exam.getStartTime());
        version.setLatestStartTime(exam.getLatestStartTime());
        version.setEndTime(exam.getEndTime());
        version.setDurationMinutes(exam.getDurationMinutes());
        version.setTimezone(exam.getTimezone());
        version.setMaxFormalSubmissions(exam.getMaxFormalSubmissions());
        version.setResultReleasePolicy(exam.getResultReleasePolicy());
        version.setResultReleaseTime(exam.getResultReleaseTime());
        version.setFeedbackPolicyJson("{\"duringExam\":\"STATUS_ONLY\",\"afterRelease\":\"FULL\"}");
        version.setIntegrityPolicyJson("{\"focus\":true,\"fullscreen\":true,\"clipboardMetadata\":true}");
        version.setPublishedBy(actorId);
        version.setPublishedTime(now);
        Map<String, Object> canonical = new LinkedHashMap<>();
        canonical.put("examId", exam.getExamId());
        canonical.put("versionNo", versionNo);
        canonical.put("title", exam.getTitle());
        canonical.put("description", exam.getDescription());
        canonical.put("startTime", exam.getStartTime());
        canonical.put("latestStartTime", exam.getLatestStartTime());
        canonical.put("endTime", exam.getEndTime());
        canonical.put("durationMinutes", exam.getDurationMinutes());
        canonical.put("timezone", exam.getTimezone());
        canonical.put("maxFormalSubmissions", exam.getMaxFormalSubmissions());
        canonical.put("resultReleasePolicy", exam.getResultReleasePolicy());
        canonical.put("resultReleaseTime", exam.getResultReleaseTime());
        canonical.put("questionHashes", questions.stream()
                .sorted(Comparator.comparing(ExamVersionQuestion::getQuestionOrder))
                .map(ExamVersionQuestion::getContentHash).toList());
        version.setContentHash(DigestUtil.sha256Hex(writeJson(canonical)));
        return version;
    }

    private String hashQuestion(ExamVersionQuestion question) {
        Map<String, Object> canonical = new LinkedHashMap<>();
        canonical.put("questionId", question.getQuestionId());
        canonical.put("questionOrder", question.getQuestionOrder());
        canonical.put("score", question.getScore());
        canonical.put("requiredFlag", question.getRequiredFlag());
        canonical.put("questionType", question.getQuestionType());
        canonical.put("title", question.getTitle());
        canonical.put("content", question.getContent());
        canonical.put("timeLimit", question.getTimeLimit());
        canonical.put("spaceLimit", question.getSpaceLimit());
        canonical.put("questionCase", question.getQuestionCase());
        canonical.put("defaultCode", question.getDefaultCode());
        canonical.put("mainFuc", question.getMainFuc());
        canonical.put("allowedLanguages", question.getAllowedLanguagesJson());
        return DigestUtil.sha256Hex(writeJson(canonical));
    }

    private ExamCommand findCommand(String type, long actorId, String key) {
        return examCommandMapper.selectOne(new LambdaQueryWrapper<ExamCommand>()
                .eq(ExamCommand::getCommandType, type)
                .eq(ExamCommand::getActorId, actorId)
                .eq(ExamCommand::getIdempotencyKey, key));
    }

    private ExamPublicationVO replayPublication(ExamCommand command, String requestHash) {
        if (!requestHash.equals(command.getRequestHash())) {
            throw new ServiceException(ResultCode.EXAM_IDEMPOTENCY_CONFLICT);
        }
        if (command.getStatus() == 0) {
            throw new ServiceException(ResultCode.EXAM_COMMAND_IN_PROGRESS);
        }
        if (command.getStatus() != 1 || command.getResponseJson() == null) {
            throw new ServiceException(ResultCode.EXAM_STATE_CONFLICT);
        }
        try {
            ExamPublicationVO result = objectMapper.readValue(command.getResponseJson(), ExamPublicationVO.class);
            result.setReplayed(true);
            return result;
        } catch (JsonProcessingException exception) {
            log.error("Cannot replay publish command {}", command.getCommandId(), exception);
            throw new ServiceException(ResultCode.ERROR);
        }
    }

    private void insertAudit(Long examId, long actorId, String action, String requestId,
                             Map<String, Object> metadata) {
        ExamAuditEvent event = new ExamAuditEvent();
        event.setExamId(examId);
        event.setActorId(actorId);
        event.setActorType("ADMIN");
        event.setAction(action);
        event.setRequestId(requestId);
        event.setResultCode(ResultCode.SUCCESS.getCode());
        event.setMetadataJson(writeJson(metadata));
        event.setServerTime(now());
        examAuditEventMapper.insert(event);
    }

    private void requireDraft(Exam exam) {
        if (ExamStatus.fromCode(exam.getStatus()) != ExamStatus.DRAFT) {
            throw new ServiceException(ResultCode.EXAM_STATE_CONFLICT);
        }
    }

    private List<Question> loadQuestions(List<ExamQuestion> relations) {
        if (relations.isEmpty()) {
            return List.of();
        }
        return questionMapper.selectBatchIds(relations.stream().map(ExamQuestion::getQuestionId).toList());
    }

    private boolean saveLegacyExamQuestions(Exam exam, Set<Long> questionIds) {
        int nextOrder = Math.toIntExact(examQuestionMapper.selectCount(
                new LambdaQueryWrapper<ExamQuestion>().eq(ExamQuestion::getExamId, exam.getExamId()))) + 1;
        for (Long questionId : questionIds) {
            ExamQuestion relation = new ExamQuestion();
            relation.setExamId(exam.getExamId());
            relation.setQuestionId(questionId);
            relation.setQuestionOrder(nextOrder++);
            relation.setScore(100);
            relation.setRequiredFlag(1);
            relation.setQuestionType(PROGRAMMING);
            examQuestionMapper.insert(relation);
        }
        return true;
    }

    private List<String> allowedActions(Exam exam) {
        ExamStatus status = ExamStatus.fromCode(exam.getStatus());
        if (status == ExamStatus.DRAFT) {
            return List.of("EDIT", "REPLACE_QUESTIONS", "PUBLISH", "DELETE");
        }
        if (status == ExamStatus.PUBLISHED && now().isBefore(exam.getStartTime())) {
            return List.of("WITHDRAW", "CANCEL", "MANAGE_CANDIDATES");
        }
        if (status == ExamStatus.PUBLISHED || status == ExamStatus.ACTIVE) {
            return List.of("CANCEL", "MANAGE_CANDIDATES", "MONITOR");
        }
        if (status == ExamStatus.FINISHED) {
            return List.of("VIEW_GRADES", "RECALCULATE_GRADES", "RELEASE_RESULTS");
        }
        return List.of("VIEW");
    }

    private ServiceException validationException(List<ValidationViolationVO> violations) {
        return new ServiceException(ResultCode.EXAM_PUBLISH_VALIDATION_FAILED,
                Map.of("violations", violations));
    }

    private boolean isJsonArray(String value) {
        if (value == null || value.isBlank()) {
            return false;
        }
        try {
            JsonNode node = objectMapper.readTree(value);
            return node.isArray() && !node.isEmpty();
        } catch (JsonProcessingException exception) {
            return false;
        }
    }

    private String writeJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException exception) {
            throw new ServiceException(ResultCode.ERROR);
        }
    }

    private ExamPublicationVO publicationVO(ExamVersion version, boolean replayed) {
        ExamPublicationVO result = new ExamPublicationVO();
        result.setVersionId(version.getVersionId());
        result.setVersionNo(version.getVersionNo());
        result.setContentHash(version.getContentHash());
        result.setPublishedBy(version.getPublishedBy());
        result.setPublishedAt(version.getPublishedTime());
        result.setReplayed(replayed);
        return result;
    }

    private void validateIdempotencyKey(String key) {
        if (key == null || key.isBlank() || key.length() > 64 || !key.chars().allMatch(c -> c >= 33 && c <= 126)) {
            throw new ServiceException(ResultCode.FAILED_PARAMS_VALIDATE,
                    Map.of("violations", List.of(new ValidationViolationVO(
                            "Idempotency-Key", "asciiMax64", "幂等键必须为不超过 64 位的 ASCII 字符"))));
        }
    }

    private String safeRequestId(String requestId, String fallback) {
        String value = requestId == null || requestId.isBlank() ? fallback : requestId;
        return value.substring(0, Math.min(64, value.length()));
    }

    private long currentActorId() {
        Long actorId = ThreadLocalUtil.get(Constants.USER_ID, Long.class);
        return actorId == null ? Constants.SYSTEM_USER_ID : actorId;
    }

    private LocalDateTime now() {
        return LocalDateTime.ofInstant(clock.instant(), ZoneOffset.UTC);
    }

    private Exam getExam(Long examId) {
        Exam exam = examMapper.selectById(examId);
        if (exam == null) {
            throw new ServiceException(ResultCode.EXAM_NOT_EXISTS);
        }
        return exam;
    }

    private String nullToEmpty(String value) {
        return value == null ? "" : value;
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
            log.warn("Exam database transaction committed but cache refresh failed", exception);
        }
    }
}
