package com.sintao.system.service.question.impl;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sintao.common.core.enums.ResultCode;
import com.sintao.common.security.exception.ServiceException;
import com.sintao.system.domain.question.dto.QuestionAddDTO;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

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

    private QuestionAddDTO baseQuestion(String type) {
        QuestionAddDTO request = new QuestionAddDTO();
        request.setTitle("测试题");
        request.setContent("题面");
        request.setQuestionType(type);
        return request;
    }
}
