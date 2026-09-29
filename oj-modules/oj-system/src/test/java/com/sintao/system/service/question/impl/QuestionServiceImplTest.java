package com.sintao.system.service.question.impl;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sintao.common.core.enums.ResultCode;
import com.sintao.common.security.exception.ServiceException;
import com.sintao.system.domain.question.dto.QuestionAddDTO;
import com.sintao.system.domain.question.dto.QuestionEditDTO;
import com.sintao.system.domain.question.Question;
import com.sintao.system.elasticsearch.SystemQuestionRepository;
import com.sintao.system.manager.QuestionCacheManager;
import com.sintao.system.mapper.question.QuestionMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class QuestionServiceImplTest {

    private QuestionServiceImpl service;

    @BeforeEach
    void setUp() {
        service = new QuestionServiceImpl();
        ReflectionTestUtils.setField(service, "objectMapper", new ObjectMapper());
    }

    @Test
    void choiceQuestionShouldRejectCorrectAnswerOutsideOptions() {
        QuestionAddDTO request = baseQuestion("SINGLE_CHOICE");
        request.setAnswerConfigJson("{\"options\":[{\"id\":\"A\",\"label\":\"甲\"},{\"id\":\"B\",\"label\":\"乙\"}]}");
        request.setGradingConfigJson("{\"correctAnswers\":[\"C\"]}");

        ServiceException exception = assertThrows(ServiceException.class, () -> service.add(request));

        assertEquals(ResultCode.FAILED_PARAMS_VALIDATE, exception.getResultCode());
    }

    @Test
    void choiceQuestionShouldRejectDuplicateOptionIds() {
        QuestionAddDTO request = baseQuestion("MULTIPLE_CHOICE");
        request.setAnswerConfigJson("{\"options\":[{\"id\":\"A\",\"label\":\"甲\"},{\"id\":\"A\",\"label\":\"乙\"}]}");
        request.setGradingConfigJson("{\"correctAnswers\":[\"A\"]}");

        ServiceException exception = assertThrows(ServiceException.class, () -> service.add(request));

        assertEquals(ResultCode.FAILED_PARAMS_VALIDATE, exception.getResultCode());
    }

    @Test
    void manualQuestionShouldRequireRubric() {
        QuestionAddDTO request = baseQuestion("SHORT_ANSWER");
        request.setAnswerConfigJson("{}");
        request.setGradingConfigJson("{}");

        ServiceException exception = assertThrows(ServiceException.class, () -> service.add(request));

        assertEquals(ResultCode.FAILED_PARAMS_VALIDATE, exception.getResultCode());
    }

    @Test
    void editingQuestionShouldPersistLanguageStarters() {
        QuestionMapper mapper = mock(QuestionMapper.class);
        SystemQuestionRepository repository = mock(SystemQuestionRepository.class);
        ReflectionTestUtils.setField(service, "questionMapper", mapper);
        ReflectionTestUtils.setField(service, "questionRepository", repository);
        Question existing = new Question();
        existing.setQuestionId(1L);
        existing.setStarterCodeJson("{\"java\":\"old\"}");
        when(mapper.selectById(1L)).thenReturn(existing);

        QuestionEditDTO request = new QuestionEditDTO();
        request.setQuestionId(1L);
        request.setTitle("A+B");
        request.setContent("Read two integers");
        request.setQuestionType("PROGRAMMING");
        request.setTimeLimit(1000L);
        request.setSpaceLimit(262144L);
        request.setQuestionCase("[{\"input\":\"1 2\",\"output\":\"3\"}]");
        request.setStarterCodeJson("{\"java\":\"new\",\"python\":\"print(3)\"}");

        service.edit(request);

        assertEquals(request.getStarterCodeJson(), existing.getStarterCodeJson());
        verify(mapper).updateById(existing);
        verify(repository).save(any());
    }

    @Test
    void addingProgrammingQuestionWithoutStartersShouldGenerateAllJudgeLanguages() throws Exception {
        QuestionMapper mapper = mock(QuestionMapper.class);
        SystemQuestionRepository repository = mock(SystemQuestionRepository.class);
        QuestionCacheManager cacheManager = mock(QuestionCacheManager.class);
        ReflectionTestUtils.setField(service, "questionMapper", mapper);
        ReflectionTestUtils.setField(service, "questionRepository", repository);
        ReflectionTestUtils.setField(service, "questionCacheManager", cacheManager);

        QuestionAddDTO request = baseQuestion("PROGRAMMING");
        request.setTimeLimit(1000L);
        request.setSpaceLimit(262144L);
        request.setQuestionCase("[{\"input\":\"1 2\",\"output\":\"3\"}]");
        request.setDefaultCode("class Legacy {}");

        service.add(request);

        JsonNode starters = new ObjectMapper().readTree(request.getStarterCodeJson());
        assertEquals("class Legacy {}", starters.path("java").asText());
        assertNotNull(starters.path("cpp").asText());
        assertNotNull(starters.path("python").asText());
        assertNotNull(starters.path("go").asText());
        verify(mapper).insert(any(Question.class));
    }

    @Test
    void editingQuestionShouldNotClobberAuthoredStartersWithGeneratedOnes() {
        QuestionMapper mapper = mock(QuestionMapper.class);
        SystemQuestionRepository repository = mock(SystemQuestionRepository.class);
        ReflectionTestUtils.setField(service, "questionMapper", mapper);
        ReflectionTestUtils.setField(service, "questionRepository", repository);
        Question existing = new Question();
        existing.setQuestionId(2L);
        existing.setQuestionType("PROGRAMMING");
        existing.setStarterCodeJson("{\"java\":\"authored\",\"cpp\":\"int main(){}\"}");
        when(mapper.selectById(2L)).thenReturn(existing);

        QuestionEditDTO request = new QuestionEditDTO();
        request.setQuestionId(2L);
        request.setTitle("A+B");
        request.setContent("Read two integers");
        request.setQuestionType("PROGRAMMING");
        request.setTimeLimit(1000L);
        request.setSpaceLimit(262144L);
        request.setQuestionCase("[{\"input\":\"1 2\",\"output\":\"3\"}]");
        request.setDefaultCode("class Legacy {}");

        service.edit(request);

        assertEquals("{\"java\":\"authored\",\"cpp\":\"int main(){}\"}", existing.getStarterCodeJson());
    }

    private QuestionAddDTO baseQuestion(String type) {
        QuestionAddDTO request = new QuestionAddDTO();
        request.setTitle("测试题");
        request.setContent("题面");
        request.setQuestionType(type);
        return request;
    }
}
