package com.sintao.friend.manager;

import com.sintao.common.core.constants.CacheConstants;
import com.sintao.common.core.enums.ResultCode;
import com.sintao.common.redis.service.RedisService;
import com.sintao.common.security.exception.ServiceException;
import com.sintao.friend.mapper.exam.ExamMapper;
import com.sintao.friend.mapper.exam.ExamQuestionMapper;
import com.sintao.friend.mapper.user.UserExamMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class ExamCacheManagerTest {

    @Mock
    private ExamMapper examMapper;

    @Mock
    private ExamQuestionMapper examQuestionMapper;

    @Mock
    private UserExamMapper userExamMapper;

    @Mock
    private RedisService redisService;

    @InjectMocks
    private ExamCacheManager examCacheManager;

    @Test
    void preQuestionShouldThrowNotExistsWhenQuestionIsMissingFromExamCache() {
        when(redisService.indexOfForList(CacheConstants.EXAM_QUESTION_LIST + 9L, 101L)).thenReturn(null);

        ServiceException exception = assertThrows(ServiceException.class, () -> examCacheManager.preQuestion(9L, 101L));

        assertEquals(ResultCode.FAILED_NOT_EXISTS.getCode(), exception.getResultCode().getCode());
    }

    @Test
    void nextQuestionShouldThrowNotExistsWhenQuestionIsMissingFromExamCache() {
        when(redisService.indexOfForList(CacheConstants.EXAM_QUESTION_LIST + 9L, 101L)).thenReturn(null);

        ServiceException exception = assertThrows(ServiceException.class, () -> examCacheManager.nextQuestion(9L, 101L));

        assertEquals(ResultCode.FAILED_NOT_EXISTS.getCode(), exception.getResultCode().getCode());
    }
}
