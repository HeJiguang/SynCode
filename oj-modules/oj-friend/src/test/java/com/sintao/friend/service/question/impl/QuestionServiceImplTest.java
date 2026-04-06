package com.sintao.friend.service.question.impl;

import com.sintao.common.core.domain.TableDataInfo;
import com.sintao.common.core.enums.ResultCode;
import com.sintao.common.security.exception.ServiceException;
import com.sintao.friend.domain.question.Question;
import com.sintao.friend.domain.question.dto.QuestionQueryDTO;
import com.sintao.friend.domain.question.es.QuestionES;
import com.sintao.friend.domain.question.vo.QuestionDetailVO;
import com.sintao.friend.elasticsearch.QuestionRepository;
import com.sintao.friend.manager.QuestionCacheManager;
import com.sintao.friend.mapper.question.QuestionMapper;
import com.sintao.friend.mapper.user.UserSubmitMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.elasticsearch.NoSuchIndexException;

import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class QuestionServiceImplTest {

    @Mock
    private QuestionRepository questionRepository;

    @Mock
    private QuestionMapper questionMapper;

    @Mock
    private UserSubmitMapper userSubmitMapper;

    @Mock
    private QuestionCacheManager questionCacheManager;

    @InjectMocks
    private QuestionServiceImpl questionService;

    @Test
    void listShouldRebuildIndexWhenQuestionIndexDoesNotExist() {
        QuestionQueryDTO queryDTO = new QuestionQueryDTO();
        queryDTO.setPageNum(1);
        queryDTO.setPageSize(10);

        Question question = new Question();
        question.setQuestionId(101L);
        question.setTitle("Only Cloud Question");
        question.setDifficulty(1);

        QuestionES questionES = new QuestionES();
        questionES.setQuestionId(101L);
        questionES.setTitle("Only Cloud Question");
        questionES.setDifficulty(1);

        when(questionRepository.count()).thenThrow(new NoSuchIndexException("idx_question"));
        when(questionMapper.selectList(any())).thenReturn(List.of(question));
        when(questionRepository.findAll(any(org.springframework.data.domain.Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(questionES)));

        TableDataInfo result = questionService.list(queryDTO);

        assertEquals(1L, result.getTotal());
        assertEquals(1, result.getRows().size());
        verify(questionRepository).saveAll(any());
    }

    @Test
    void detailShouldFallbackToDatabaseWhenQuestionIndexDoesNotExist() {
        Question question = new Question();
        question.setQuestionId(101L);
        question.setTitle("Only Cloud Question");
        question.setDifficulty(1);
        question.setContent("from db");

        when(questionRepository.findById(101L)).thenThrow(new NoSuchIndexException("idx_question"));
        when(questionMapper.selectById(101L)).thenReturn(question);
        when(questionMapper.selectList(any())).thenReturn(List.of(question));

        QuestionDetailVO detail = questionService.detail(101L);

        assertNotNull(detail);
        assertEquals(101L, detail.getQuestionId());
        assertEquals("Only Cloud Question", detail.getTitle());
        verify(questionRepository).saveAll(any());
    }

    @Test
    void preQuestionShouldRefreshCacheAndRetryWhenQuestionIsMissingFromRedisIndex() {
        when(questionCacheManager.getListSize()).thenReturn(1L);
        when(questionCacheManager.preQuestion(101L))
                .thenThrow(new ServiceException(ResultCode.FAILED_NOT_EXISTS))
                .thenReturn(100L);
        doNothing().when(questionCacheManager).refreshCache();

        String previousQuestionId = questionService.preQuestion(101L);

        assertEquals("100", previousQuestionId);
        verify(questionCacheManager).refreshCache();
    }
}
