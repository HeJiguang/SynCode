package com.sintao.system.service.question.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.collection.CollectionUtil;
import cn.hutool.core.util.StrUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.github.pagehelper.PageHelper;
import com.sintao.common.core.constants.Constants;
import com.sintao.common.core.enums.ResultCode;
import com.sintao.common.core.enums.QuestionType;
import com.sintao.common.security.exception.ServiceException;
import com.sintao.system.domain.question.Question;
import com.sintao.system.domain.question.dto.QuestionAddDTO;
import com.sintao.system.domain.question.dto.QuestionEditDTO;
import com.sintao.system.domain.question.dto.QuestionQueryDTO;
import com.sintao.system.domain.question.es.QuestionES;
import com.sintao.system.domain.question.vo.QuestionDetailVO;
import com.sintao.system.domain.question.vo.QuestionVO;
import com.sintao.system.elasticsearch.SystemQuestionRepository;
import com.sintao.system.manager.QuestionCacheManager;
import com.sintao.system.mapper.question.QuestionMapper;
import com.sintao.system.service.question.IQuestionService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

@Service
@Slf4j
public class QuestionServiceImpl implements IQuestionService {

    @Autowired
    private QuestionMapper questionMapper;

    @Autowired
    private SystemQuestionRepository questionRepository;

    @Autowired
    private QuestionCacheManager questionCacheManager;

    @Autowired
    private ObjectMapper objectMapper;

    @Override
    public List<QuestionVO> list(QuestionQueryDTO questionQueryDTO) {
        String excludeIdStr = questionQueryDTO.getExcludeIdStr();
        if (StrUtil.isNotEmpty(excludeIdStr)) {
            String[] excludeIdArr = excludeIdStr.split(Constants.SPLIT_SEM);
            Set<Long> excludeIdSet = Arrays.stream(excludeIdArr)
                    .map(Long::valueOf)
                    .collect(Collectors.toSet());
            questionQueryDTO.setExcludeIdSet(excludeIdSet);
        }
        PageHelper.startPage(questionQueryDTO.getPageNum(), questionQueryDTO.getPageSize());
        return questionMapper.selectQuestionList(questionQueryDTO);
    }

    @Override
    public boolean add(QuestionAddDTO questionAddDTO) {
        normalizeAndValidate(questionAddDTO);
        List<Question> questionList = questionMapper.selectList(new LambdaQueryWrapper<Question>()
                .eq(Question::getTitle, questionAddDTO.getTitle()));
        if (CollectionUtil.isNotEmpty(questionList)) {
            throw new ServiceException(ResultCode.FAILED_ALREADY_EXISTS);
        }
        Question question = new Question();
        BeanUtil.copyProperties(questionAddDTO, question);
        int insert = questionMapper.insert(question);
        if (insert <= 0) {
            return false;
        }
        QuestionES questionES = new QuestionES();
        BeanUtil.copyProperties(question, questionES);
        questionRepository.save(questionES);
        questionCacheManager.addCache(question.getQuestionId());
        return true;
    }

    @Override
    public QuestionDetailVO detail(Long questionId) {
        Question question = questionMapper.selectById(questionId);
        if (question == null) {
            throw new ServiceException(ResultCode.FAILED_NOT_EXISTS);
        }
        QuestionDetailVO questionDetailVO = new QuestionDetailVO();
        BeanUtil.copyProperties(question, questionDetailVO);
        return questionDetailVO;
    }

    @Override
    public int edit(QuestionEditDTO questionEditDTO) {
        normalizeAndValidate(questionEditDTO);
        Question oldQuestion = questionMapper.selectById(questionEditDTO.getQuestionId());
        if (oldQuestion == null) {
            throw new ServiceException(ResultCode.FAILED_NOT_EXISTS);
        }
        oldQuestion.setTitle(questionEditDTO.getTitle());
        oldQuestion.setDifficulty(questionEditDTO.getDifficulty());
        oldQuestion.setAlgorithmTag(questionEditDTO.getAlgorithmTag());
        oldQuestion.setKnowledgeTags(questionEditDTO.getKnowledgeTags());
        oldQuestion.setEstimatedMinutes(questionEditDTO.getEstimatedMinutes());
        oldQuestion.setTrainingEnabled(questionEditDTO.getTrainingEnabled());
        oldQuestion.setQuestionType(questionEditDTO.getQuestionType());
        oldQuestion.setAnswerConfigJson(questionEditDTO.getAnswerConfigJson());
        oldQuestion.setGradingConfigJson(questionEditDTO.getGradingConfigJson());
        oldQuestion.setTimeLimit(questionEditDTO.getTimeLimit());
        oldQuestion.setSpaceLimit(questionEditDTO.getSpaceLimit());
        oldQuestion.setContent(questionEditDTO.getContent());
        oldQuestion.setQuestionCase(questionEditDTO.getQuestionCase());
        oldQuestion.setDefaultCode(questionEditDTO.getDefaultCode());
        oldQuestion.setMainFuc(questionEditDTO.getMainFuc());
        QuestionES questionES = new QuestionES();
        BeanUtil.copyProperties(oldQuestion, questionES);
        questionRepository.save(questionES);
        return questionMapper.updateById(oldQuestion);
    }

    @Override
    public int delete(Long questionId) {
        Question question = questionMapper.selectById(questionId);
        if (question == null) {
            throw new ServiceException(ResultCode.FAILED_NOT_EXISTS);
        }
        questionRepository.deleteById(questionId);
        questionCacheManager.deleteCache(questionId);
        return questionMapper.deleteById(questionId);
    }

    private void normalizeAndValidate(QuestionAddDTO request) {
        if (request == null || StrUtil.isBlank(request.getTitle()) || StrUtil.isBlank(request.getContent())) {
            throw new ServiceException(ResultCode.FAILED_PARAMS_VALIDATE);
        }
        QuestionType type;
        try {
            type = QuestionType.from(request.getQuestionType());
        } catch (IllegalArgumentException exception) {
            throw new ServiceException(ResultCode.FAILED_PARAMS_VALIDATE);
        }
        request.setQuestionType(type.name());
        JsonNode answerConfig = readObject(request.getAnswerConfigJson(), "{}");
        JsonNode gradingConfig = readObject(request.getGradingConfigJson(), "{}");
        request.setAnswerConfigJson(answerConfig.toString());
        request.setGradingConfigJson(gradingConfig.toString());

        if (type.isObjective()
                && (!gradingConfig.path("correctAnswers").isArray()
                || gradingConfig.path("correctAnswers").isEmpty())) {
            throw new ServiceException(ResultCode.FAILED_PARAMS_VALIDATE);
        }
        if (type == QuestionType.SINGLE_CHOICE || type == QuestionType.MULTIPLE_CHOICE) {
            validateChoiceConfig(type, answerConfig, gradingConfig);
        }
        if (type == QuestionType.TRUE_FALSE) {
            JsonNode answers = gradingConfig.path("correctAnswers");
            String answer = answers.size() == 1 ? answers.get(0).asText() : "";
            if (!("true".equals(answer) || "false".equals(answer))) {
                throw new ServiceException(ResultCode.FAILED_PARAMS_VALIDATE);
            }
        }
        if (!type.isObjective() && type != QuestionType.PROGRAMMING
                && StrUtil.isBlank(gradingConfig.path("rubric").asText())) {
            throw new ServiceException(ResultCode.FAILED_PARAMS_VALIDATE);
        }
        if (type == QuestionType.PROGRAMMING) {
            if (request.getTimeLimit() == null || request.getTimeLimit() <= 0
                    || request.getSpaceLimit() == null || request.getSpaceLimit() <= 0
                    || !readArray(request.getQuestionCase())) {
                throw new ServiceException(ResultCode.FAILED_PARAMS_VALIDATE);
            }
        } else {
            if (request.getTimeLimit() == null || request.getTimeLimit() <= 0) request.setTimeLimit(1000L);
            if (request.getSpaceLimit() == null || request.getSpaceLimit() <= 0) request.setSpaceLimit(262144L);
            if (request.getQuestionCase() == null) request.setQuestionCase("[]");
            if (request.getDefaultCode() == null) request.setDefaultCode("");
            if (request.getMainFuc() == null) request.setMainFuc("");
        }
    }

    private void validateChoiceConfig(QuestionType type, JsonNode answerConfig, JsonNode gradingConfig) {
        JsonNode options = answerConfig.path("options");
        if (!options.isArray() || options.size() < 2) {
            throw new ServiceException(ResultCode.FAILED_PARAMS_VALIDATE);
        }
        Set<String> optionIds = new HashSet<>();
        for (JsonNode option : options) {
            String id = option.path("id").asText().trim();
            String label = option.path("label").asText().trim();
            if (id.isEmpty() || label.isEmpty() || !optionIds.add(id)) {
                throw new ServiceException(ResultCode.FAILED_PARAMS_VALIDATE);
            }
        }
        JsonNode correctAnswers = gradingConfig.path("correctAnswers");
        if (type == QuestionType.SINGLE_CHOICE && correctAnswers.size() != 1) {
            throw new ServiceException(ResultCode.FAILED_PARAMS_VALIDATE);
        }
        Set<String> correctIds = new HashSet<>();
        for (JsonNode answer : correctAnswers) {
            String id = answer.asText().trim();
            if (!optionIds.contains(id) || !correctIds.add(id)) {
                throw new ServiceException(ResultCode.FAILED_PARAMS_VALIDATE);
            }
        }
    }

    private JsonNode readObject(String value, String fallback) {
        try {
            JsonNode node = objectMapper.readTree(StrUtil.blankToDefault(value, fallback));
            if (node == null || !node.isObject()) throw new IllegalArgumentException();
            return node;
        } catch (Exception exception) {
            throw new ServiceException(ResultCode.FAILED_PARAMS_VALIDATE);
        }
    }

    private boolean readArray(String value) {
        try {
            JsonNode node = objectMapper.readTree(value);
            return node != null && node.isArray() && !node.isEmpty();
        } catch (Exception exception) {
            return false;
        }
    }
}
