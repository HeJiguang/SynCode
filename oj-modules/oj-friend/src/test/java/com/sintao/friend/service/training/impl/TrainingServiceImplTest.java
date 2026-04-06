package com.sintao.friend.service.training.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.sintao.common.core.constants.Constants;
import com.sintao.common.core.utils.ThreadLocalUtil;
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
import com.sintao.friend.domain.user.UserExam;
import com.sintao.friend.domain.user.UserSubmit;
import com.sintao.friend.mapper.exam.ExamMapper;
import com.sintao.friend.mapper.question.QuestionMapper;
import com.sintao.friend.mapper.training.TrainingPlanMapper;
import com.sintao.friend.mapper.training.TrainingProfileMapper;
import com.sintao.friend.mapper.training.TrainingTaskMapper;
import com.sintao.friend.mapper.user.UserExamMapper;
import com.sintao.friend.mapper.user.UserSubmitMapper;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import java.time.LocalDateTime;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class TrainingServiceImplTest {

    @Mock
    private TrainingProfileMapper trainingProfileMapper;

    @Mock
    private TrainingPlanMapper trainingPlanMapper;

    @Mock
    private TrainingTaskMapper trainingTaskMapper;

    @Mock
    private QuestionMapper questionMapper;

    @Mock
    private UserSubmitMapper userSubmitMapper;

    @Mock
    private UserExamMapper userExamMapper;

    @Mock
    private TrainingAgentClient trainingAgentClient;

    @Mock
    private ExamMapper examMapper;

    @InjectMocks
    private TrainingServiceImpl trainingService;

    @BeforeEach
    void setUp() {
        ReflectionTestUtils.setField(trainingService, "candidateLimit", 40);
    }

    @AfterEach
    void tearDown() {
        ThreadLocalUtil.remove();
    }

    @Test
    void generateShouldPassCandidateExamsToTrainingAgent() {
        Question question = new Question();
        question.setQuestionId(101L);
        question.setTitle("Two Sum");
        question.setDifficulty(1);
        question.setTrainingEnabled(1);

        Exam exam = new Exam();
        exam.setExamId(9001L);
        exam.setTitle("Stage Checkpoint");
        exam.setStartTime(LocalDateTime.now().minusHours(1));
        exam.setEndTime(LocalDateTime.now().plusHours(2));
        exam.setStatus(1);

        AgentTrainingPlanRequest request = ReflectionTestUtils.invokeMethod(
                trainingService,
                "buildAgentRequest",
                new TrainingGenerateDTO(),
                99L,
                null,
                Collections.emptyList(),
                Collections.emptyMap(),
                List.of(question),
                List.of(exam)
        );

        assertEquals(1, request.getCandidateExams().size());
        assertEquals(9001L, request.getCandidateExams().get(0).getExamId());
        assertEquals("Stage Checkpoint", request.getCandidateExams().get(0).getTitle());
    }

    @Test
    void loadCandidateQuestionsShouldFallbackToGeneralQuestionPoolWhenTrainingPoolIsEmpty() {
        Question fallbackQuestion = new Question();
        fallbackQuestion.setQuestionId(101L);
        fallbackQuestion.setTitle("Two Sum");
        fallbackQuestion.setDifficulty(1);
        fallbackQuestion.setTrainingEnabled(0);
        when(questionMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(Collections.emptyList(), List.of(fallbackQuestion));

        List<Question> candidates = ReflectionTestUtils.invokeMethod(trainingService, "loadCandidateQuestions");

        assertEquals(1, candidates.size());
        assertEquals(101L, candidates.get(0).getQuestionId());
    }

    @Test
    void finishTaskShouldUpdateLastTestExamIdWhenTestTaskCompletes() {
        ThreadLocalUtil.set(Constants.USER_ID, 99L);

        TrainingTask task = new TrainingTask();
        task.setTaskId(500L);
        task.setPlanId(700L);
        task.setUserId(99L);
        task.setTaskType("test");
        task.setExamId(9001L);
        task.setTaskStatus(0);

        TrainingProfile profile = new TrainingProfile();
        profile.setProfileId(301L);
        profile.setUserId(99L);

        TrainingTaskFinishDTO finishDTO = new TrainingTaskFinishDTO();
        finishDTO.setTaskId(500L);

        when(trainingTaskMapper.selectById(500L)).thenReturn(task);
        when(trainingTaskMapper.updateById(any(TrainingTask.class))).thenReturn(1);
        TrainingTask pendingSiblingTask = new TrainingTask();
        pendingSiblingTask.setTaskId(501L);
        pendingSiblingTask.setPlanId(700L);
        pendingSiblingTask.setUserId(99L);
        pendingSiblingTask.setTaskStatus(0);

        when(trainingTaskMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(task, pendingSiblingTask));
        when(trainingProfileMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(profile);

        boolean result = trainingService.finishTask(finishDTO);

        assertTrue(result);
        assertEquals(9001L, profile.getLastTestExamId());
    }

    @Test
    void currentShouldMarkScoredTestTaskDoneAndSyncPlanState() {
        ThreadLocalUtil.set(Constants.USER_ID, 99L);

        TrainingProfile profile = new TrainingProfile();
        profile.setProfileId(301L);
        profile.setUserId(99L);
        profile.setCurrentLevel("starter");
        profile.setTargetDirection("algorithm_foundation");

        TrainingPlan plan = new TrainingPlan();
        plan.setPlanId(700L);
        plan.setUserId(99L);
        plan.setPlanTitle("Stage recovery cycle");
        plan.setPlanGoal("Finish the checkpoint");
        plan.setPlanStatus(1);

        TrainingTask task = new TrainingTask();
        task.setTaskId(500L);
        task.setPlanId(700L);
        task.setUserId(99L);
        task.setTaskType("test");
        task.setExamId(9001L);
        task.setTaskStatus(0);
        task.setTaskOrder(1);
        task.setTitleSnapshot("Binary Search Checkpoint");

        UserExam userExam = new UserExam();
        userExam.setUserExamId(801L);
        userExam.setExamId(9001L);
        userExam.setUserId(99L);
        userExam.setScore(300);
        userExam.setExamRank(2);
        userExam.setUpdateTime(LocalDateTime.of(2026, 3, 26, 11, 15));

        when(trainingProfileMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(profile);
        when(trainingPlanMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(plan);
        when(trainingTaskMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(task));
        when(userExamMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(userExam);
        when(trainingTaskMapper.updateById(any(TrainingTask.class))).thenReturn(1);
        when(trainingProfileMapper.updateById(any(TrainingProfile.class))).thenReturn(1);
        when(trainingPlanMapper.updateById(any(TrainingPlan.class))).thenReturn(1);

        TrainingCurrentVO current = trainingService.current();

        assertEquals(1, current.getTasks().size());
        assertEquals(1, current.getTasks().get(0).getTaskStatus());
        assertEquals(2, current.getPlanStatus());
        assertEquals(9001L, profile.getLastTestExamId());
        assertEquals("scored", current.getTasks().get(0).getResultStatus());
        assertEquals(300, current.getTasks().get(0).getResultScore());
        assertEquals(2, current.getTasks().get(0).getResultRank());
    }

    @Test
    void currentShouldExposeSubmittedStageTestWithoutMarkingTaskDone() {
        ThreadLocalUtil.set(Constants.USER_ID, 99L);

        TrainingProfile profile = new TrainingProfile();
        profile.setProfileId(301L);
        profile.setUserId(99L);

        TrainingPlan plan = new TrainingPlan();
        plan.setPlanId(700L);
        plan.setUserId(99L);
        plan.setPlanStatus(1);

        TrainingTask task = new TrainingTask();
        task.setTaskId(500L);
        task.setPlanId(700L);
        task.setUserId(99L);
        task.setTaskType("test");
        task.setExamId(9001L);
        task.setTaskStatus(0);
        task.setTaskOrder(1);
        task.setCreateTime(LocalDateTime.of(2026, 3, 26, 10, 0));

        UserSubmit latestSubmit = new UserSubmit();
        latestSubmit.setSubmitId(901L);
        latestSubmit.setExamId(9001L);
        latestSubmit.setUserId(99L);
        latestSubmit.setScore(100);
        latestSubmit.setPass(1);
        latestSubmit.setUpdateTime(LocalDateTime.of(2026, 3, 26, 10, 30));

        Exam exam = new Exam();
        exam.setExamId(9001L);
        exam.setEndTime(LocalDateTime.now().plusHours(1));

        when(trainingProfileMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(profile);
        when(trainingPlanMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(plan);
        when(trainingTaskMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(task));
        when(userExamMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(null);
        when(userSubmitMapper.selectLatestExamSubmit(99L, 9001L, task.getCreateTime())).thenReturn(latestSubmit);
        when(examMapper.selectById(9001L)).thenReturn(exam);

        TrainingCurrentVO current = trainingService.current();

        assertEquals(1, current.getTasks().size());
        assertEquals(0, current.getTasks().get(0).getTaskStatus());
        assertEquals(1, current.getPlanStatus());
        assertEquals("submitted", current.getTasks().get(0).getResultStatus());
        assertEquals(100, current.getTasks().get(0).getResultScore());
    }
}
