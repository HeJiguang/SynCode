package com.sintao.friend.service.training.impl;

import cn.hutool.core.util.StrUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.sintao.common.core.constants.Constants;
import com.sintao.common.core.enums.ResultCode;
import com.sintao.common.core.utils.ThreadLocalUtil;
import com.sintao.common.security.exception.ServiceException;
import com.sintao.friend.client.TrainingAgentClient;
import com.sintao.friend.client.dto.AgentTrainingPlanRequest;
import com.sintao.friend.client.dto.AgentTrainingPlanResponse;
import com.sintao.friend.domain.exam.Exam;
import com.sintao.friend.domain.question.Question;
import com.sintao.friend.domain.training.TrainingPlan;
import com.sintao.friend.domain.training.TrainingProfile;
import com.sintao.friend.domain.training.TrainingTask;
import com.sintao.friend.domain.training.dto.TrainingGenerateDTO;
import com.sintao.friend.domain.training.dto.TrainingTaskFinishDTO;
import com.sintao.friend.domain.training.vo.TrainingCurrentVO;
import com.sintao.friend.domain.training.vo.TrainingTaskVO;
import com.sintao.friend.domain.user.UserExam;
import com.sintao.friend.domain.user.UserSubmit;
import com.sintao.friend.mapper.exam.ExamMapper;
import com.sintao.friend.mapper.question.QuestionMapper;
import com.sintao.friend.mapper.training.TrainingPlanMapper;
import com.sintao.friend.mapper.training.TrainingProfileMapper;
import com.sintao.friend.mapper.training.TrainingTaskMapper;
import com.sintao.friend.mapper.user.UserExamMapper;
import com.sintao.friend.mapper.user.UserSubmitMapper;
import com.sintao.friend.service.training.ITrainingService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
public class TrainingServiceImpl implements ITrainingService {

    private static final int PLAN_STATUS_ACTIVE = 1;
    private static final int PLAN_STATUS_DONE = 2;
    private static final int PLAN_STATUS_EXPIRED = 3;
    private static final int TASK_STATUS_PENDING = 0;
    private static final int TASK_STATUS_DONE = 1;

    @Autowired
    private TrainingProfileMapper trainingProfileMapper;

    @Autowired
    private TrainingPlanMapper trainingPlanMapper;

    @Autowired
    private TrainingTaskMapper trainingTaskMapper;

    @Autowired
    private QuestionMapper questionMapper;

    @Autowired
    private UserSubmitMapper userSubmitMapper;

    @Autowired
    private UserExamMapper userExamMapper;

    @Autowired
    private TrainingAgentClient trainingAgentClient;

    @Autowired
    private ExamMapper examMapper;

    @Value("${training.agent.candidate-limit:40}")
    private Integer candidateLimit;

    @Override
    public TrainingProfile profile() {
        Long userId = currentUserId();
        TrainingProfile profile = loadProfile(userId);
        return profile != null ? profile : buildDefaultProfile(userId);
    }

    @Override
    public TrainingCurrentVO current() {
        Long userId = currentUserId();
        TrainingProfile profile = loadProfile(userId);
        TrainingPlan plan = loadCurrentPlan(userId);
        TrainingCurrentVO currentVO = new TrainingCurrentVO();
        if (plan == null) {
            fillProfilePart(currentVO, profile, userId);
            return currentVO;
        }
        List<TrainingTask> tasks = loadTasks(plan.getPlanId(), userId);
        TrainingProfile effectiveProfile = syncCurrentPlanState(plan, tasks, profile, userId);
        fillProfilePart(currentVO, effectiveProfile, userId);
        fillPlanPart(currentVO, plan);
        currentVO.setTasks(tasks.stream()
                .sorted(Comparator.comparing(TrainingTask::getTaskOrder))
                .map(this::toTaskVO)
                .collect(Collectors.toList()));
        return currentVO;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public TrainingCurrentVO generate(TrainingGenerateDTO trainingGenerateDTO) {
        Long userId = currentUserId();
        TrainingGenerateDTO requestDTO = trainingGenerateDTO == null ? new TrainingGenerateDTO() : trainingGenerateDTO;
        TrainingProfile profile = loadProfile(userId);

        List<UserSubmit> recentSubmissions = loadRecentSubmissions(userId);
        Map<Long, Question> recentQuestionMap = loadQuestionMap(
                recentSubmissions.stream()
                        .map(UserSubmit::getQuestionId)
                        .filter(Objects::nonNull)
                        .distinct()
                        .collect(Collectors.toList())
        );
        List<Question> candidateQuestions = loadCandidateQuestions();
        List<Exam> candidateExams = loadCandidateExams();

        AgentTrainingPlanRequest agentRequest = buildAgentRequest(
                requestDTO,
                userId,
                profile,
                recentSubmissions,
                recentQuestionMap,
                candidateQuestions,
                candidateExams
        );
        AgentTrainingPlanResponse agentResponse = trainingAgentClient.generatePlan(agentRequest);
        if (agentResponse == null || agentResponse.getTasks() == null || agentResponse.getTasks().isEmpty()) {
            throw new ServiceException(ResultCode.ERROR);
        }

        expireActivePlans(userId);

        TrainingPlan trainingPlan = new TrainingPlan();
        trainingPlan.setUserId(userId);
        trainingPlan.setPlanTitle(defaultIfBlank(agentResponse.getPlanTitle(), "AI personalized training plan"));
        trainingPlan.setPlanGoal(defaultIfBlank(agentResponse.getPlanGoal(), "Build a stable algorithm practice routine"));
        trainingPlan.setSourceType(defaultIfBlank(requestDTO.getSourceType(), "manual_refresh"));
        trainingPlan.setBasedOnExamId(requestDTO.getBasedOnExamId());
        trainingPlan.setPlanStatus(PLAN_STATUS_ACTIVE);
        trainingPlan.setAiSummary(agentResponse.getAiSummary());
        trainingPlanMapper.insert(trainingPlan);

        List<TrainingTask> trainingTasks = buildTasks(userId, trainingPlan.getPlanId(), agentResponse);
        for (TrainingTask trainingTask : trainingTasks) {
            trainingTaskMapper.insert(trainingTask);
        }

        TrainingProfile savedProfile = upsertProfile(profile, userId, requestDTO, trainingPlan, agentResponse);

        TrainingCurrentVO currentVO = new TrainingCurrentVO();
        fillProfilePart(currentVO, savedProfile, userId);
        fillPlanPart(currentVO, trainingPlan);
        currentVO.setTasks(trainingTasks.stream()
                .sorted(Comparator.comparing(TrainingTask::getTaskOrder))
                .map(this::toTaskVO)
                .collect(Collectors.toList()));
        return currentVO;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public boolean finishTask(TrainingTaskFinishDTO trainingTaskFinishDTO) {
        if (trainingTaskFinishDTO == null || trainingTaskFinishDTO.getTaskId() == null) {
            throw new ServiceException(ResultCode.FAILED_PARAMS_VALIDATE);
        }

        Long userId = currentUserId();
        TrainingTask trainingTask = trainingTaskMapper.selectById(trainingTaskFinishDTO.getTaskId());
        if (trainingTask == null || !userId.equals(trainingTask.getUserId())) {
            throw new ServiceException(ResultCode.FAILED_NOT_EXISTS);
        }

        trainingTask.setTaskStatus(trainingTaskFinishDTO.getTaskStatus() == null
                ? TASK_STATUS_DONE
                : trainingTaskFinishDTO.getTaskStatus());
        int updated = trainingTaskMapper.updateById(trainingTask);
        if (updated <= 0) {
            return false;
        }

        List<TrainingTask> taskList = trainingTaskMapper.selectList(new LambdaQueryWrapper<TrainingTask>()
                .eq(TrainingTask::getPlanId, trainingTask.getPlanId())
                .eq(TrainingTask::getUserId, userId));
        refreshProfileAfterTaskFinish(trainingTask, userId);
        boolean allFinished = taskList.stream()
                .allMatch(task -> task.getTaskStatus() != null && task.getTaskStatus() != TASK_STATUS_PENDING);
        if (allFinished) {
            trainingPlanMapper.update(null, new LambdaUpdateWrapper<TrainingPlan>()
                    .eq(TrainingPlan::getPlanId, trainingTask.getPlanId())
                    .set(TrainingPlan::getPlanStatus, PLAN_STATUS_DONE));
        }
        return true;
    }

    private void refreshProfileAfterTaskFinish(TrainingTask trainingTask, Long userId) {
        if (!"test".equalsIgnoreCase(trainingTask.getTaskType()) || trainingTask.getExamId() == null) {
            return;
        }
        TrainingProfile profile = loadProfile(userId);
        if (profile == null) {
            profile = buildDefaultProfile(userId);
            profile.setLastTestExamId(trainingTask.getExamId());
            trainingProfileMapper.insert(profile);
            return;
        }
        profile.setLastTestExamId(trainingTask.getExamId());
        trainingProfileMapper.updateById(profile);
    }

    private TrainingProfile syncCurrentPlanState(TrainingPlan plan, List<TrainingTask> tasks, TrainingProfile profile, Long userId) {
        TrainingProfile effectiveProfile = profile;
        boolean profileChanged = false;
        for (TrainingTask task : tasks) {
            TestTaskSnapshot snapshot = buildTestTaskSnapshot(task, userId);
            if (snapshot == null) {
                continue;
            }
            task.setResultStatus(snapshot.getResultStatus());
            task.setResultScore(snapshot.getResultScore());
            task.setResultRank(snapshot.getResultRank());
            task.setResultUpdatedAt(snapshot.getResultUpdatedAt());
            if (snapshot.isShouldMarkDone() && !Objects.equals(task.getTaskStatus(), TASK_STATUS_DONE)) {
                task.setTaskStatus(TASK_STATUS_DONE);
                trainingTaskMapper.updateById(task);
            }
            if (snapshot.isShouldSyncProfile()) {
                effectiveProfile = ensureProfile(effectiveProfile, userId);
                if (!Objects.equals(effectiveProfile.getLastTestExamId(), task.getExamId())) {
                    effectiveProfile.setLastTestExamId(task.getExamId());
                    profileChanged = true;
                }
            }
        }
        if (profileChanged) {
            trainingProfileMapper.updateById(effectiveProfile);
        }
        if (tasks.stream().allMatch(this::isTaskFinished) && !Objects.equals(plan.getPlanStatus(), PLAN_STATUS_DONE)) {
            TrainingPlan savedPlan = new TrainingPlan();
            savedPlan.setPlanId(plan.getPlanId());
            savedPlan.setPlanStatus(PLAN_STATUS_DONE);
            trainingPlanMapper.updateById(savedPlan);
            plan.setPlanStatus(PLAN_STATUS_DONE);
        }
        return effectiveProfile;
    }

    private Long currentUserId() {
        Long userId = ThreadLocalUtil.get(Constants.USER_ID, Long.class);
        if (userId == null) {
            throw new ServiceException(ResultCode.FAILED_USER_NOT_EXISTS);
        }
        return userId;
    }

    private TrainingProfile loadProfile(Long userId) {
        return trainingProfileMapper.selectOne(new LambdaQueryWrapper<TrainingProfile>()
                .eq(TrainingProfile::getUserId, userId)
                .last("limit 1"));
    }

    private TrainingPlan loadCurrentPlan(Long userId) {
        TrainingPlan currentPlan = trainingPlanMapper.selectOne(new LambdaQueryWrapper<TrainingPlan>()
                .eq(TrainingPlan::getUserId, userId)
                .eq(TrainingPlan::getPlanStatus, PLAN_STATUS_ACTIVE)
                .orderByDesc(TrainingPlan::getPlanId)
                .last("limit 1"));
        if (currentPlan != null) {
            return currentPlan;
        }
        return trainingPlanMapper.selectOne(new LambdaQueryWrapper<TrainingPlan>()
                .eq(TrainingPlan::getUserId, userId)
                .orderByDesc(TrainingPlan::getPlanId)
                .last("limit 1"));
    }

    private List<UserSubmit> loadRecentSubmissions(Long userId) {
        return userSubmitMapper.selectList(new LambdaQueryWrapper<UserSubmit>()
                .eq(UserSubmit::getUserId, userId)
                .orderByDesc(UserSubmit::getSubmitId)
                .last("limit 20"));
    }

    private List<Question> loadCandidateQuestions() {
        int limit = candidateLimit == null || candidateLimit <= 0 ? 40 : candidateLimit;
        List<Question> trainingQuestions = questionMapper.selectList(new LambdaQueryWrapper<Question>()
                .and(wrapper -> wrapper.eq(Question::getTrainingEnabled, 1).or().isNull(Question::getTrainingEnabled))
                .orderByAsc(Question::getDifficulty)
                .orderByAsc(Question::getQuestionId)
                .last("limit " + limit));
        if (trainingQuestions != null && !trainingQuestions.isEmpty()) {
            return trainingQuestions;
        }
        List<Question> fallbackQuestions = questionMapper.selectList(new LambdaQueryWrapper<Question>()
                .orderByAsc(Question::getDifficulty)
                .orderByAsc(Question::getQuestionId)
                .last("limit " + limit));
        return fallbackQuestions == null ? Collections.emptyList() : fallbackQuestions;
    }

    private List<Exam> loadCandidateExams() {
        return examMapper.selectList(new LambdaQueryWrapper<Exam>()
                .eq(Exam::getStatus, 1)
                .and(wrapper -> wrapper.isNull(Exam::getEndTime).or().gt(Exam::getEndTime, LocalDateTime.now()))
                .orderByAsc(Exam::getStartTime)
                .orderByAsc(Exam::getExamId)
                .last("limit 3"));
    }

    private Map<Long, Question> loadQuestionMap(List<Long> questionIds) {
        if (questionIds == null || questionIds.isEmpty()) {
            return Collections.emptyMap();
        }
        return questionMapper.selectBatchIds(questionIds).stream()
                .filter(Objects::nonNull)
                .collect(Collectors.toMap(Question::getQuestionId, question -> question, (left, right) -> left, HashMap::new));
    }

    private AgentTrainingPlanRequest buildAgentRequest(
            TrainingGenerateDTO trainingGenerateDTO,
            Long userId,
            TrainingProfile profile,
            List<UserSubmit> recentSubmissions,
            Map<Long, Question> recentQuestionMap,
            List<Question> candidateQuestions,
            List<Exam> candidateExams) {
        AgentTrainingPlanRequest request = new AgentTrainingPlanRequest();
        request.setTraceId(UUID.randomUUID().toString());
        request.setUserId(userId);
        request.setCurrentLevel(profile == null ? "starter" : defaultIfBlank(profile.getCurrentLevel(), "starter"));
        request.setTargetDirection(resolveTargetDirection(trainingGenerateDTO, profile));
        request.setBasedOnExamId(trainingGenerateDTO.getBasedOnExamId());
        request.setPreferredCount(trainingGenerateDTO.getPreferredCount() == null || trainingGenerateDTO.getPreferredCount() <= 0
                ? 5
                : trainingGenerateDTO.getPreferredCount());

        List<AgentTrainingPlanRequest.SubmissionSnapshot> submissionSnapshots = new ArrayList<>();
        for (UserSubmit recentSubmission : recentSubmissions) {
            AgentTrainingPlanRequest.SubmissionSnapshot snapshot = new AgentTrainingPlanRequest.SubmissionSnapshot();
            snapshot.setSubmitId(recentSubmission.getSubmitId());
            snapshot.setQuestionId(recentSubmission.getQuestionId());
            snapshot.setExamId(recentSubmission.getExamId());
            snapshot.setPass(recentSubmission.getPass());
            snapshot.setScore(recentSubmission.getScore());
            snapshot.setExeMessage(recentSubmission.getExeMessage());
            Question question = recentQuestionMap.get(recentSubmission.getQuestionId());
            if (question != null) {
                snapshot.setTitle(question.getTitle());
                snapshot.setDifficulty(question.getDifficulty());
                snapshot.setAlgorithmTag(question.getAlgorithmTag());
                snapshot.setKnowledgeTags(question.getKnowledgeTags());
            }
            submissionSnapshots.add(snapshot);
        }
        request.setRecentSubmissions(submissionSnapshots);

        List<AgentTrainingPlanRequest.QuestionCandidate> questionCandidates = new ArrayList<>();
        for (Question candidateQuestion : candidateQuestions) {
            AgentTrainingPlanRequest.QuestionCandidate questionCandidate = new AgentTrainingPlanRequest.QuestionCandidate();
            questionCandidate.setQuestionId(candidateQuestion.getQuestionId());
            questionCandidate.setTitle(candidateQuestion.getTitle());
            questionCandidate.setDifficulty(candidateQuestion.getDifficulty());
            questionCandidate.setAlgorithmTag(candidateQuestion.getAlgorithmTag());
            questionCandidate.setKnowledgeTags(candidateQuestion.getKnowledgeTags());
            questionCandidate.setEstimatedMinutes(candidateQuestion.getEstimatedMinutes());
            questionCandidates.add(questionCandidate);
        }
        request.setCandidateQuestions(questionCandidates);

        List<AgentTrainingPlanRequest.ExamCandidate> examCandidates = new ArrayList<>();
        for (Exam candidateExam : candidateExams) {
            AgentTrainingPlanRequest.ExamCandidate examCandidate = new AgentTrainingPlanRequest.ExamCandidate();
            examCandidate.setExamId(candidateExam.getExamId());
            examCandidate.setTitle(defaultIfBlank(candidateExam.getTitle(), "Stage test checkpoint"));
            examCandidate.setStartTime(candidateExam.getStartTime() == null ? null : candidateExam.getStartTime().toString());
            examCandidate.setEndTime(candidateExam.getEndTime() == null ? null : candidateExam.getEndTime().toString());
            examCandidates.add(examCandidate);
        }
        request.setCandidateExams(examCandidates);
        return request;
    }

    private List<TrainingTask> buildTasks(Long userId, Long planId, AgentTrainingPlanResponse agentResponse) {
        List<TrainingTask> taskList = new ArrayList<>();
        int nextTaskOrder = 1;
        for (AgentTrainingPlanResponse.PlanTask planTask : agentResponse.getTasks()) {
            TrainingTask trainingTask = new TrainingTask();
            trainingTask.setPlanId(planId);
            trainingTask.setUserId(userId);
            trainingTask.setTaskType(defaultIfBlank(planTask.getTaskType(), "question"));
            trainingTask.setQuestionId(planTask.getQuestionId());
            trainingTask.setExamId(planTask.getExamId());
            trainingTask.setTitleSnapshot(defaultIfBlank(planTask.getTitleSnapshot(), "Training task"));
            trainingTask.setTaskOrder(planTask.getTaskOrder() == null ? nextTaskOrder : planTask.getTaskOrder());
            trainingTask.setTaskStatus(TASK_STATUS_PENDING);
            trainingTask.setRecommendedReason(planTask.getRecommendedReason());
            trainingTask.setKnowledgeTagsSnapshot(planTask.getKnowledgeTagsSnapshot());
            trainingTask.setDueTime(planTask.getDueTime());
            taskList.add(trainingTask);
            nextTaskOrder++;
        }
        return taskList;
    }

    private TrainingProfile upsertProfile(
            TrainingProfile existingProfile,
            Long userId,
            TrainingGenerateDTO trainingGenerateDTO,
            TrainingPlan trainingPlan,
            AgentTrainingPlanResponse agentResponse) {
        TrainingProfile profile = existingProfile == null ? new TrainingProfile() : existingProfile;
        profile.setUserId(userId);
        profile.setCurrentLevel(defaultIfBlank(agentResponse.getCurrentLevel(), "starter"));
        profile.setTargetDirection(defaultIfBlank(agentResponse.getTargetDirection(), resolveTargetDirection(trainingGenerateDTO, existingProfile)));
        profile.setWeakPoints(agentResponse.getWeakPoints());
        profile.setStrongPoints(agentResponse.getStrongPoints());
        profile.setLastTestExamId(resolveLatestTestExamId(trainingGenerateDTO, agentResponse));
        profile.setLastPlanId(trainingPlan.getPlanId());
        profile.setStatus(1);
        if (existingProfile == null) {
            trainingProfileMapper.insert(profile);
        } else {
            trainingProfileMapper.updateById(profile);
        }
        return profile;
    }

    private Long resolveLatestTestExamId(TrainingGenerateDTO trainingGenerateDTO, AgentTrainingPlanResponse agentResponse) {
        if (trainingGenerateDTO != null && trainingGenerateDTO.getBasedOnExamId() != null) {
            return trainingGenerateDTO.getBasedOnExamId();
        }
        if (agentResponse == null || agentResponse.getTasks() == null) {
            return null;
        }
        return agentResponse.getTasks().stream()
                .filter(Objects::nonNull)
                .filter(task -> "test".equalsIgnoreCase(task.getTaskType()))
                .map(AgentTrainingPlanResponse.PlanTask::getExamId)
                .filter(Objects::nonNull)
                .findFirst()
                .orElse(null);
    }

    private void expireActivePlans(Long userId) {
        trainingPlanMapper.update(null, new LambdaUpdateWrapper<TrainingPlan>()
                .eq(TrainingPlan::getUserId, userId)
                .in(TrainingPlan::getPlanStatus, 0, PLAN_STATUS_ACTIVE)
                .set(TrainingPlan::getPlanStatus, PLAN_STATUS_EXPIRED));
    }

    private List<TrainingTask> loadTasks(Long planId, Long userId) {
        return trainingTaskMapper.selectList(new LambdaQueryWrapper<TrainingTask>()
                .eq(TrainingTask::getPlanId, planId)
                .eq(TrainingTask::getUserId, userId)
                .orderByAsc(TrainingTask::getTaskOrder));
    }

    private TrainingTaskVO toTaskVO(TrainingTask trainingTask) {
        TrainingTaskVO trainingTaskVO = new TrainingTaskVO();
        trainingTaskVO.setTaskId(trainingTask.getTaskId());
        trainingTaskVO.setTaskType(trainingTask.getTaskType());
        trainingTaskVO.setQuestionId(trainingTask.getQuestionId());
        trainingTaskVO.setExamId(trainingTask.getExamId());
        trainingTaskVO.setTitleSnapshot(trainingTask.getTitleSnapshot());
        trainingTaskVO.setTaskOrder(trainingTask.getTaskOrder());
        trainingTaskVO.setTaskStatus(trainingTask.getTaskStatus());
        trainingTaskVO.setRecommendedReason(trainingTask.getRecommendedReason());
        trainingTaskVO.setKnowledgeTagsSnapshot(trainingTask.getKnowledgeTagsSnapshot());
        trainingTaskVO.setDueTime(trainingTask.getDueTime());
        trainingTaskVO.setResultStatus(trainingTask.getResultStatus());
        trainingTaskVO.setResultScore(trainingTask.getResultScore());
        trainingTaskVO.setResultRank(trainingTask.getResultRank());
        trainingTaskVO.setResultUpdatedAt(trainingTask.getResultUpdatedAt());
        return trainingTaskVO;
    }

    private void fillProfilePart(TrainingCurrentVO currentVO, TrainingProfile profile, Long userId) {
        TrainingProfile effectiveProfile = profile == null ? buildDefaultProfile(userId) : profile;
        currentVO.setCurrentLevel(effectiveProfile.getCurrentLevel());
        currentVO.setTargetDirection(effectiveProfile.getTargetDirection());
        currentVO.setWeakPoints(effectiveProfile.getWeakPoints());
        currentVO.setStrongPoints(effectiveProfile.getStrongPoints());
    }

    private void fillPlanPart(TrainingCurrentVO currentVO, TrainingPlan trainingPlan) {
        currentVO.setPlanId(trainingPlan.getPlanId());
        currentVO.setPlanTitle(trainingPlan.getPlanTitle());
        currentVO.setPlanGoal(trainingPlan.getPlanGoal());
        currentVO.setPlanStatus(trainingPlan.getPlanStatus());
        currentVO.setAiSummary(trainingPlan.getAiSummary());
    }

    private TrainingProfile buildDefaultProfile(Long userId) {
        TrainingProfile trainingProfile = new TrainingProfile();
        trainingProfile.setUserId(userId);
        trainingProfile.setCurrentLevel("starter");
        trainingProfile.setTargetDirection("algorithm_foundation");
        trainingProfile.setWeakPoints("Generate your first plan to identify weak points.");
        trainingProfile.setStrongPoints("Training summary will appear after the first plan.");
        trainingProfile.setStatus(1);
        return trainingProfile;
    }

    private String resolveTargetDirection(TrainingGenerateDTO trainingGenerateDTO, TrainingProfile trainingProfile) {
        if (trainingGenerateDTO != null && StrUtil.isNotBlank(trainingGenerateDTO.getTargetDirection())) {
            return trainingGenerateDTO.getTargetDirection();
        }
        if (trainingProfile != null && StrUtil.isNotBlank(trainingProfile.getTargetDirection())) {
            return trainingProfile.getTargetDirection();
        }
        return "algorithm_foundation";
    }

    private String defaultIfBlank(String value, String defaultValue) {
        return StrUtil.isBlank(value) ? defaultValue : value;
    }

    private TestTaskSnapshot buildTestTaskSnapshot(TrainingTask task, Long userId) {
        if (task == null || !"test".equalsIgnoreCase(task.getTaskType()) || task.getExamId() == null) {
            return null;
        }
        UserExam userExam = userExamMapper.selectOne(new LambdaQueryWrapper<UserExam>()
                .eq(UserExam::getUserId, userId)
                .eq(UserExam::getExamId, task.getExamId())
                .last("limit 1"));
        UserSubmit latestSubmit = userSubmitMapper.selectLatestExamSubmit(userId, task.getExamId(), task.getCreateTime());
        Exam exam = examMapper.selectById(task.getExamId());
        boolean examEnded = exam != null && exam.getEndTime() != null && !exam.getEndTime().isAfter(LocalDateTime.now());

        TestTaskSnapshot snapshot = new TestTaskSnapshot();
        if (userExam != null && userExam.getScore() != null) {
            snapshot.setResultStatus("scored");
            snapshot.setResultScore(userExam.getScore());
            snapshot.setResultRank(userExam.getExamRank());
            snapshot.setResultUpdatedAt(userExam.getUpdateTime() != null ? userExam.getUpdateTime() : userExam.getCreateTime());
            snapshot.setShouldMarkDone(true);
            snapshot.setShouldSyncProfile(true);
            return snapshot;
        }
        if (latestSubmit != null) {
            snapshot.setResultStatus(examEnded ? "completed_pending_score" : "submitted");
            snapshot.setResultScore(latestSubmit.getScore());
            snapshot.setResultUpdatedAt(latestSubmit.getUpdateTime() != null ? latestSubmit.getUpdateTime() : latestSubmit.getCreateTime());
            snapshot.setShouldMarkDone(examEnded);
            snapshot.setShouldSyncProfile(examEnded);
            return snapshot;
        }
        if (userExam != null) {
            snapshot.setResultStatus("entered");
        }
        return snapshot.getResultStatus() == null ? null : snapshot;
    }

    private TrainingProfile ensureProfile(TrainingProfile profile, Long userId) {
        if (profile != null) {
            return profile;
        }
        TrainingProfile createdProfile = buildDefaultProfile(userId);
        trainingProfileMapper.insert(createdProfile);
        return createdProfile;
    }

    private boolean isTaskFinished(TrainingTask task) {
        return task.getTaskStatus() != null && task.getTaskStatus() != TASK_STATUS_PENDING;
    }

    @lombok.Getter
    @lombok.Setter
    private static class TestTaskSnapshot {

        private String resultStatus;

        private Integer resultScore;

        private Integer resultRank;

        private LocalDateTime resultUpdatedAt;

        private boolean shouldMarkDone;

        private boolean shouldSyncProfile;
    }
}
