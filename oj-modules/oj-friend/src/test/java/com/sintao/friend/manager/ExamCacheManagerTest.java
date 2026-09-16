package com.sintao.friend.manager;

import com.sintao.common.core.constants.CacheConstants;
import com.sintao.common.core.enums.ExamListType;
import com.sintao.common.core.enums.ResultCode;
import com.sintao.common.redis.service.RedisService;
import com.sintao.common.security.exception.ServiceException;
import com.sintao.friend.domain.exam.dto.ExamQueryDTO;
import com.sintao.friend.domain.exam.vo.ExamVO;
import com.sintao.friend.mapper.exam.ExamMapper;
import com.sintao.friend.mapper.exam.ExamQuestionMapper;
import com.sintao.friend.mapper.user.UserExamMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.anyMap;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
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

    @Test
    void examListShouldRefreshLegacyCachedSummaries() {
        long userId = 7L;
        long examId = 9L;
        String listKey = CacheConstants.USER_EXAM_LIST + userId;
        String detailKey = CacheConstants.EXAM_DETAIL + examId;
        ExamVO legacy = new ExamVO();
        legacy.setExamId(examId);
        legacy.setTitle("Legacy cached exam");
        ExamVO enriched = new ExamVO();
        enriched.setExamId(examId);
        enriched.setTitle("Mixed exam");
        enriched.setDurationMinutes(90);
        enriched.setQuestionCount(9);
        enriched.setStatus(2);
        enriched.setTimezone("Asia/Shanghai");
        ExamQueryDTO query = new ExamQueryDTO();
        query.setType(ExamListType.USER_EXAM_LIST.getValue());

        when(redisService.getCacheListByRange(listKey, 0, 9, Long.class)).thenReturn(List.of(examId));
        when(redisService.multiGet(List.of(detailKey), ExamVO.class)).thenReturn(List.of(legacy));
        when(userExamMapper.selectUserExamList(userId)).thenReturn(List.of(enriched));

        List<ExamVO> result = examCacheManager.getExamVOList(query, userId);

        assertEquals(1, result.size());
        assertEquals(90, result.get(0).getDurationMinutes());
        assertEquals(9, result.get(0).getQuestionCount());
        assertEquals("Asia/Shanghai", result.get(0).getTimezone());
        verify(userExamMapper, times(2)).selectUserExamList(userId);
        verify(redisService).multiSet(anyMap());
    }
}
