package com.sintao.friend.service.question.impl;

import com.sintao.common.core.domain.TableDataInfo;
import com.sintao.common.core.enums.ResultCode;
import com.sintao.common.security.exception.ServiceException;
import com.sintao.friend.domain.question.Question;
import com.sintao.friend.domain.question.dto.QuestionQueryDTO;
import com.sintao.friend.domain.question.es.QuestionES;
import com.sintao.friend.domain.question.vo.QuestionDetailVO;
import com.sintao.friend.domain.question.vo.QuestionVO;
import com.sintao.friend.elasticsearch.FriendQuestionRepository;
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
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class QuestionServiceImplTest {

    @Mock
    private FriendQuestionRepository questionRepository;

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
        questionES.setAlgorithmTag("hash");
        questionES.setKnowledgeTags("array,hash");
        questionES.setEstimatedMinutes(15);
        questionES.setTrainingEnabled(1);

        when(questionRepository.count()).thenThrow(new NoSuchIndexException("idx_question"));
        when(questionMapper.selectList(any())).thenReturn(List.of(question));
        when(questionRepository.findAll(any(org.springframework.data.domain.Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(questionES)));

        TableDataInfo result = questionService.list(queryDTO);

        assertEquals(1L, result.getTotal());
        assertEquals(1, result.getRows().size());
        QuestionVO row = (QuestionVO) result.getRows().get(0);
        assertEquals("hash", row.getAlgorithmTag());
        assertEquals("array,hash", row.getKnowledgeTags());
        assertEquals(15, row.getEstimatedMinutes());
        assertEquals(1, row.getTrainingEnabled());
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

    @Test
    void detailShouldExpandLegacyJavaStarterToAllJudgeLanguages() {
        Question question = new Question();
        question.setQuestionId(102L);
        question.setTitle("Legacy Java Question");
        question.setDifficulty(1);
        question.setContent("from db");
        question.setDefaultCode("import java.util.*;");

        when(questionRepository.findById(102L)).thenReturn(Optional.empty());
        when(questionMapper.selectById(102L)).thenReturn(question);
        when(questionMapper.selectList(any())).thenReturn(List.of(question));

        QuestionDetailVO detail = questionService.detail(102L);

        assertNotNull(detail);
        assertNotNull(detail.getStarterCode());
        assertEquals(4, detail.getStarterCode().size());
        assertEquals("import java.util.*;", detail.getStarterCode().get("java"));
        assertNotNull(detail.getStarterCode().get("cpp"));
        assertNotNull(detail.getStarterCode().get("python"));
        assertNotNull(detail.getStarterCode().get("go"));
    }

    @Test
    void detailShouldExpandInvalidStarterJsonToAllJudgeLanguages() {
        QuestionES questionES = new QuestionES();
        questionES.setQuestionId(103L);
        questionES.setTitle("Broken Starter JSON");
        questionES.setDifficulty(1);
        questionES.setContent("from es");
        questionES.setStarterCodeJson("{not-json");
        questionES.setDefaultCode("class Legacy {}");

        when(questionRepository.findById(103L)).thenReturn(Optional.of(questionES));

        QuestionDetailVO detail = questionService.detail(103L);

        assertNotNull(detail);
        assertEquals(4, detail.getStarterCode().size());
        assertEquals("class Legacy {}", detail.getStarterCode().get("java"));
    }

    @Test
    void detailShouldKeepAuthoredStartersAndFillMissingJavaFromLegacyCode() {
        QuestionES questionES = new QuestionES();
        questionES.setQuestionId(104L);
        questionES.setTitle("Partial Starter JSON");
        questionES.setDifficulty(1);
        questionES.setContent("from es");
        questionES.setStarterCodeJson("{\"cpp\":\"int main(){}\",\"python\":\"pass\",\"go\":\"x\"}");
        questionES.setDefaultCode("class LegacyMain {}");

        when(questionRepository.findById(104L)).thenReturn(Optional.of(questionES));

        QuestionDetailVO detail = questionService.detail(104L);

        assertNotNull(detail);
        assertEquals("int main(){}", detail.getStarterCode().get("cpp"));
        assertEquals("class LegacyMain {}", detail.getStarterCode().get("java"));
    }

    @Test
    void detailShouldExpandJavaOnlyStarterJsonToAllJudgeLanguages() {
        QuestionES questionES = new QuestionES();
        questionES.setQuestionId(106L);
        questionES.setTitle("Legacy Java Only Starter");
        questionES.setDifficulty(1);
        questionES.setContent("from es");
        questionES.setStarterCodeJson("{\"java\":\"class AuthoredMain {}\"}");
        questionES.setDefaultCode("class AuthoredMain {}");

        when(questionRepository.findById(106L)).thenReturn(Optional.of(questionES));

        QuestionDetailVO detail = questionService.detail(106L);

        assertNotNull(detail);
        assertEquals(4, detail.getStarterCode().size());
        assertEquals("class AuthoredMain {}", detail.getStarterCode().get("java"));
        assertFalse(detail.getStarterCode().get("cpp").isBlank());
        assertFalse(detail.getStarterCode().get("python").isBlank());
        assertFalse(detail.getStarterCode().get("go").isBlank());
    }

    @Test
    void detailShouldHealStaleIndexDocumentFromDatabase() {
        QuestionES questionES = new QuestionES();
        questionES.setQuestionId(105L);
        questionES.setTitle("Stale Index Document");
        questionES.setDifficulty(1);
        questionES.setContent("from es");
        questionES.setDefaultCode("class LegacyMain {}");

        Question question = new Question();
        question.setQuestionId(105L);
        question.setStarterCodeJson("{\"java\":\"class Authored {}\",\"cpp\":\"int main(){}\"}");

        when(questionRepository.findById(105L)).thenReturn(Optional.of(questionES));
        when(questionMapper.selectById(105L)).thenReturn(question);

        QuestionDetailVO detail = questionService.detail(105L);

        assertNotNull(detail);
        assertEquals("class Authored {}", detail.getStarterCode().get("java"));
        assertEquals("int main(){}", detail.getStarterCode().get("cpp"));
        verify(questionRepository).save(questionES);
    }
}
