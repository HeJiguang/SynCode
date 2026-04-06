package com.sintao.friend.manager;

import com.sintao.common.core.constants.CacheConstants;
import com.sintao.common.core.enums.ResultCode;
import com.sintao.common.redis.service.RedisService;
import com.sintao.common.security.exception.ServiceException;
import com.sintao.friend.mapper.question.QuestionMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class QuestionCacheManagerTest {

    @Mock
    private RedisService redisService;

    @Mock
    private QuestionMapper questionMapper;

    @InjectMocks
    private QuestionCacheManager questionCacheManager;

    @Test
    void preQuestionShouldThrowNotExistsWhenQuestionIsMissingFromCache() {
        when(redisService.indexOfForList(CacheConstants.QUESTION_LIST, 101L)).thenReturn(null);

        ServiceException exception = assertThrows(ServiceException.class, () -> questionCacheManager.preQuestion(101L));

        assertEquals(ResultCode.FAILED_NOT_EXISTS.getCode(), exception.getResultCode().getCode());
    }

    @Test
    void nextQuestionShouldThrowNotExistsWhenQuestionIsMissingFromCache() {
        when(redisService.indexOfForList(CacheConstants.QUESTION_LIST, 101L)).thenReturn(null);

        ServiceException exception = assertThrows(ServiceException.class, () -> questionCacheManager.nextQuestion(101L));

        assertEquals(ResultCode.FAILED_NOT_EXISTS.getCode(), exception.getResultCode().getCode());
        verify(redisService).indexOfForList(CacheConstants.QUESTION_LIST, 101L);
    }
}
