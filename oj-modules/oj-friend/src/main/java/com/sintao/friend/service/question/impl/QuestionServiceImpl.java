package com.sintao.friend.service.question.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.collection.CollectionUtil;
import cn.hutool.core.util.StrUtil;
import cn.hutool.json.JSONUtil;
import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.TypeReference;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.github.pagehelper.PageHelper;
import com.sintao.common.core.constants.Constants;
import com.sintao.common.core.domain.TableDataInfo;
import com.sintao.common.core.enums.ResultCode;
import com.sintao.common.core.utils.LegacyJsonRepair;
import com.sintao.common.core.utils.MultiLanguageStarterCodes;
import com.sintao.common.security.exception.ServiceException;
import com.sintao.friend.domain.question.Question;
import com.sintao.friend.domain.question.QuestionCase;
import com.sintao.friend.domain.question.dto.QuestionQueryDTO;
import com.sintao.friend.domain.question.es.QuestionES;
import com.sintao.friend.domain.question.vo.QuestionCaseVO;
import com.sintao.friend.domain.question.vo.QuestionDetailVO;
import com.sintao.friend.domain.question.vo.QuestionVO;
import com.sintao.friend.elasticsearch.FriendQuestionRepository;
import com.sintao.friend.manager.QuestionCacheManager;
import com.sintao.friend.mapper.question.QuestionMapper;
import com.sintao.friend.mapper.user.UserSubmitMapper;
import com.sintao.friend.service.question.IQuestionService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
@Slf4j
public class QuestionServiceImpl implements IQuestionService {

    @Autowired
    private FriendQuestionRepository questionRepository;

    @Autowired
    private QuestionMapper questionMapper;

    @Autowired
    private UserSubmitMapper userSubmitMapper;

    @Autowired
    private QuestionCacheManager questionCacheManager;

    @Override
    public TableDataInfo list(QuestionQueryDTO questionQueryDTO) {
        Sort sort = Sort.by(Sort.Direction.DESC, "createTime");
        Pageable pageable = PageRequest.of(questionQueryDTO.getPageNum() - 1, questionQueryDTO.getPageSize(), sort);
        Integer difficulty = questionQueryDTO.getDifficulty();
        String keyword = questionQueryDTO.getKeyword();
        Page<QuestionES> questionESPage;
        if (difficulty == null && StrUtil.isEmpty(keyword)) {
            questionESPage = questionRepository.findLive(pageable);
        } else if (StrUtil.isEmpty(keyword)) {
            questionESPage = questionRepository.findQuestionByDifficulty(difficulty, pageable);
        } else if (difficulty == null) {
            questionESPage = questionRepository.findByTitleOrContent(keyword, keyword, pageable);
        } else {
            questionESPage = questionRepository.findByTitleOrContentAndDifficulty(keyword, keyword, difficulty, pageable);
        }
        long total = questionESPage.getTotalElements();
        if (total <= 0) {
            return TableDataInfo.empty();
        }
        List<QuestionES> questionESList = questionESPage.getContent();
        List<QuestionVO> questionVOList = BeanUtil.copyToList(questionESList, QuestionVO.class);
        return TableDataInfo.success(questionVOList, total);
    }

    @Override
    public List<QuestionVO> hotList() {
        List<Long> ids;
        try {
            ids = questionCacheManager.getHostList();
            if (CollectionUtil.isNotEmpty(ids)) return assembleQuestionVOList(ids);
            String generation = questionCacheManager.hotGeneration();
            ids = loadHotIds();
            questionCacheManager.refreshHotQuestionList(ids, generation);
        } catch (org.springframework.dao.DataAccessException failure) {
            log.warn("Redis hot-list unavailable; reading MySQL");
            ids = loadHotIds();
        }
        return assembleQuestionVOList(ids);
    }

    private List<Long> loadHotIds() {
        PageHelper.startPage(Constants.HOST_QUESTION_LIST_START, Constants.HOST_QUESTION_LIST_END);
        return userSubmitMapper.selectHostQuestionList();
    }

    @Override
    public QuestionDetailVO detail(Long questionId) {
        QuestionDetailVO questionDetailVO = new QuestionDetailVO();
        Question question = questionMapper.selectById(questionId);
        if (question == null) {
            return null;
        }
        BeanUtil.copyProperties(question, questionDetailVO);
        questionDetailVO.setStarterCode(parseStarterCode(question.getStarterCodeJson(), question.getDefaultCode()));
        questionDetailVO.setExampleCases(extractExampleCases(question.getQuestionCase()));
        return questionDetailVO;
    }

    @Override
    public String preQuestion(Long questionId) {
        return navigate(questionId, -1);
    }

    @Override
    public String nextQuestion(Long questionId) {
        return navigate(questionId, 1);
    }

    private String navigate(Long questionId, int direction) {
        try {
            if (questionCacheManager.getListSize() == null || questionCacheManager.getListSize() == 0) {
                questionCacheManager.refreshCache();
            }
            try {
                Object id = direction < 0 ? questionCacheManager.preQuestion(questionId) : questionCacheManager.nextQuestion(questionId);
                if (id != null && questionMapper.selectById(Long.valueOf(id.toString())) != null) return id.toString();
            } catch (ServiceException failure) {
                // Re-evaluate boundaries and missing IDs against authoritative ordering below.
            }
        } catch (org.springframework.dao.DataAccessException failure) {
            log.warn("Redis navigation unavailable; reading MySQL");
        }
        List<Long> ids = questionMapper.selectList(new LambdaQueryWrapper<Question>()
                .select(Question::getQuestionId).orderByDesc(Question::getCreateTime)
                .orderByDesc(Question::getQuestionId)).stream().map(Question::getQuestionId).toList();
        int index = ids.indexOf(questionId);
        if (index < 0) throw new ServiceException(ResultCode.FAILED_NOT_EXISTS);
        int next = index + direction;
        if (next < 0) throw new ServiceException(ResultCode.FAILED_FIRST_QUESTION);
        if (next >= ids.size()) throw new ServiceException(ResultCode.FAILED_LAST_QUESTION);
        return ids.get(next).toString();
    }

    private List<QuestionVO> assembleQuestionVOList(List<Long> hotQuestionIdList) {
        if (CollectionUtil.isEmpty(hotQuestionIdList)) {
            return new ArrayList<>();
        }
        List<QuestionVO> resultList = new ArrayList<>();
        for (Long questionId : hotQuestionIdList) {
            QuestionDetailVO detail = detail(questionId);
            if (detail == null) {
                continue;
            }
            QuestionVO questionVO = new QuestionVO();
            questionVO.setQuestionId(detail.getQuestionId());
            questionVO.setTitle(detail.getTitle());
            questionVO.setDifficulty(detail.getDifficulty());
            resultList.add(questionVO);
        }
        return resultList;
    }

    private List<QuestionCaseVO> extractExampleCases(String questionCaseJson) {
        if (StrUtil.isBlank(questionCaseJson)) {
            return new ArrayList<>();
        }
        List<QuestionCase> questionCaseList = JSONUtil.toList(
                LegacyJsonRepair.escapeControlCharsInStrings(questionCaseJson), QuestionCase.class);
        if (CollectionUtil.isEmpty(questionCaseList)) {
            return new ArrayList<>();
        }
        return questionCaseList.stream()
                .limit(2)
                .map(this::toQuestionCaseVO)
                .collect(Collectors.toList());
    }

    private Map<String, String> parseStarterCode(String starterCodeJson, String legacyJavaCode) {
        if (StrUtil.isBlank(starterCodeJson)) {
            return MultiLanguageStarterCodes.buildStarterMap(legacyJavaCode);
        }
        try {
            Map<String, String> starters = JSON.parseObject(starterCodeJson, new TypeReference<>() { });
            if (CollectionUtil.isEmpty(starters)) {
                return MultiLanguageStarterCodes.buildStarterMap(legacyJavaCode);
            }
            if (StrUtil.isBlank(starters.get(MultiLanguageStarterCodes.JAVA))) {
                starters.put(MultiLanguageStarterCodes.JAVA, MultiLanguageStarterCodes.javaStarterOrDefault(legacyJavaCode));
            }
            return MultiLanguageStarterCodes.expandStarterMap(starters);
        } catch (RuntimeException exception) {
            log.warn("Invalid starter code JSON; expanding legacy starter to judge-pool languages", exception);
            return MultiLanguageStarterCodes.buildStarterMap(legacyJavaCode);
        }
    }

    private QuestionCaseVO toQuestionCaseVO(QuestionCase questionCase) {
        QuestionCaseVO caseVO = new QuestionCaseVO();
        caseVO.setInput(questionCase.getInput());
        caseVO.setOutput(questionCase.getOutput());
        return caseVO;
    }
}
