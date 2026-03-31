package com.sintao.friend.service.user.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.collection.CollectionUtil;
import cn.hutool.core.util.StrUtil;
import cn.hutool.json.JSONUtil;
import com.alibaba.fastjson2.JSON;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.sintao.api.RemoteJudgeService;
import com.sintao.api.domain.UserExeResult;
import com.sintao.api.domain.dto.JudgeSubmitDTO;
import com.sintao.api.domain.vo.UserCodeRunVO;
import com.sintao.api.domain.vo.UserQuestionResultVO;
import com.sintao.common.core.constants.Constants;
import com.sintao.common.core.domain.R;
import com.sintao.common.core.enums.JudgeAsyncStatus;
import com.sintao.common.core.enums.ProgramType;
import com.sintao.common.core.enums.QuestionResType;
import com.sintao.common.core.enums.ResultCode;
import com.sintao.common.core.utils.ThreadLocalUtil;
import com.sintao.common.redis.service.JudgeRuntimeStateService;
import com.sintao.common.security.exception.ServiceException;
import com.sintao.friend.domain.question.Question;
import com.sintao.friend.domain.question.QuestionCase;
import com.sintao.friend.domain.question.es.QuestionES;
import com.sintao.friend.domain.user.UserSubmit;
import com.sintao.friend.domain.user.dto.UserRunDTO;
import com.sintao.friend.domain.user.dto.UserSubmitDTO;
import com.sintao.friend.domain.user.vo.AsyncSubmitResponseVO;
import com.sintao.friend.domain.user.vo.UserSubmissionHistoryVO;
import com.sintao.friend.elasticsearch.QuestionRepository;
import com.sintao.friend.mapper.question.QuestionMapper;
import com.sintao.friend.mapper.user.UserSubmitMapper;
import com.sintao.friend.rabbit.JudgeProducer;
import com.sintao.friend.service.user.IUserQuestionService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
@Slf4j
public class UserQuestionServiceImpl implements IUserQuestionService {

    @Autowired
    private QuestionRepository questionRepository;

    @Autowired
    private QuestionMapper questionMapper;

    @Autowired
    private UserSubmitMapper userSubmitMapper;

    @Autowired
    private RemoteJudgeService remoteJudgeService;

    @Autowired
    private JudgeProducer judgeProducer;

    @Autowired
    private JudgeRuntimeStateService judgeRuntimeStateService;

    @Override
    public R<UserCodeRunVO> run(UserRunDTO runDTO) {
        Integer programType = runDTO.getProgramType();
        if (ProgramType.JAVA.getValue().equals(programType)) {
            RunPayload runPayload = buildRunPayload(runDTO.getQuestionId(), runDTO.getCustomInputs());
            JudgeSubmitDTO judgeSubmitDTO = assembleJudgeSubmitDTO(
                    runDTO.getQuestionId(),
                    runDTO.getExamId(),
                    runDTO.getProgramType(),
                    runDTO.getUserCode(),
                    runPayload.inputList(),
                    runPayload.outputList()
            );
            return remoteJudgeService.runJavaCode(judgeSubmitDTO);
        }
        throw new ServiceException(ResultCode.FAILED_NOT_SUPPORT_PROGRAM);
    }

    @Override
    public R<UserQuestionResultVO> submit(UserSubmitDTO submitDTO) {
        Integer programType = submitDTO.getProgramType();
        if (ProgramType.JAVA.getValue().equals(programType)) {
            JudgeSubmitDTO judgeSubmitDTO = assembleJudgeSubmitDTO(
                    submitDTO.getQuestionId(),
                    submitDTO.getExamId(),
                    submitDTO.getProgramType(),
                    submitDTO.getUserCode(),
                    null,
                    null
            );
            return remoteJudgeService.doJudgeJavaCode(judgeSubmitDTO);
        }
        throw new ServiceException(ResultCode.FAILED_NOT_SUPPORT_PROGRAM);
    }

    @Override
    public AsyncSubmitResponseVO rabbitSubmit(UserSubmitDTO submitDTO) {
        Integer programType = submitDTO.getProgramType();
        if (ProgramType.JAVA.getValue().equals(programType)) {
            JudgeSubmitDTO judgeSubmitDTO = assembleJudgeSubmitDTO(
                    submitDTO.getQuestionId(),
                    submitDTO.getExamId(),
                    submitDTO.getProgramType(),
                    submitDTO.getUserCode(),
                    null,
                    null
            );
            judgeSubmitDTO.setRequestId(UUID.randomUUID().toString().replace("-", ""));
            userSubmitMapper.insert(buildAcceptedSubmit(judgeSubmitDTO));
            judgeRuntimeStateService.markAccepted(judgeSubmitDTO.getRequestId());
            judgeProducer.produceMsg(judgeSubmitDTO);
            AsyncSubmitResponseVO responseVO = new AsyncSubmitResponseVO();
            responseVO.setRequestId(judgeSubmitDTO.getRequestId());
            responseVO.setStatus("ACCEPTED");
            return responseVO;
        }
        throw new ServiceException(ResultCode.FAILED_NOT_SUPPORT_PROGRAM);
    }

    @Override
    public UserQuestionResultVO exeResult(Long examId, Long questionId, String currentTime, String requestId) {
        Long userId = ThreadLocalUtil.get(Constants.USER_ID, Long.class);
        UserSubmit userSubmit = getCurrentSubmit(userId, examId, questionId, currentTime, requestId);
        UserQuestionResultVO resultVO = new UserQuestionResultVO();
        if (userSubmit == null) {
            resultVO.setPass(QuestionResType.IN_JUDGE.getValue());
        } else {
            resultVO.setPass(userSubmit.getPass());
            resultVO.setExeMessage(userSubmit.getExeMessage());
            resultVO.setUseTime(userSubmit.getUseTime());
            resultVO.setUseMemory(userSubmit.getUseMemory());
            if (StrUtil.isNotEmpty(userSubmit.getCaseJudgeRes())) {
                resultVO.setUserExeResultList(JSON.parseArray(userSubmit.getCaseJudgeRes(), UserExeResult.class));
            }
        }
        return resultVO;
    }

    @Override
    public List<UserSubmissionHistoryVO> submissionHistory(Long examId, Long questionId) {
        Long userId = ThreadLocalUtil.get(Constants.USER_ID, Long.class);
        return userSubmitMapper.selectSubmissionHistory(userId, examId, questionId, 20).stream()
                .map(this::toSubmissionHistoryVO)
                .collect(Collectors.toList());
    }

    private JudgeSubmitDTO assembleJudgeSubmitDTO(Long questionId,
                                                  Long examId,
                                                  Integer programType,
                                                  String userCode,
                                                  List<String> inputOverrides,
                                                  List<String> outputOverrides) {
        QuestionES questionES = loadQuestion(questionId);
        JudgeSubmitDTO judgeSubmitDTO = new JudgeSubmitDTO();
        BeanUtil.copyProperties(questionES, judgeSubmitDTO);
        judgeSubmitDTO.setUserId(ThreadLocalUtil.get(Constants.USER_ID, Long.class));
        judgeSubmitDTO.setExamId(examId);
        judgeSubmitDTO.setProgramType(programType);
        judgeSubmitDTO.setUserCode(codeConnect(userCode, questionES.getMainFuc()));

        if (inputOverrides != null && outputOverrides != null) {
            judgeSubmitDTO.setInputList(inputOverrides);
            judgeSubmitDTO.setOutputList(outputOverrides);
            return judgeSubmitDTO;
        }

        List<QuestionCase> questionCaseList = extractQuestionCaseList(questionES.getQuestionCase());
        judgeSubmitDTO.setInputList(questionCaseList.stream().map(QuestionCase::getInput).toList());
        judgeSubmitDTO.setOutputList(questionCaseList.stream().map(QuestionCase::getOutput).toList());
        return judgeSubmitDTO;
    }

    private QuestionES loadQuestion(Long questionId) {
        QuestionES questionES = questionRepository.findById(questionId).orElse(null);
        if (questionES != null) {
            return questionES;
        }
        Question question = questionMapper.selectById(questionId);
        if (question == null) {
            throw new ServiceException(ResultCode.FAILED);
        }
        QuestionES fallback = new QuestionES();
        BeanUtil.copyProperties(question, fallback);
        questionRepository.save(fallback);
        return fallback;
    }

    private List<QuestionCase> extractQuestionCaseList(String questionCaseJson) {
        if (StrUtil.isBlank(questionCaseJson)) {
            return List.of();
        }
        return JSONUtil.toList(questionCaseJson, QuestionCase.class);
    }

    private RunPayload buildRunPayload(Long questionId, List<String> customInputs) {
        QuestionES questionES = loadQuestion(questionId);
        List<QuestionCase> sampleCases = extractQuestionCaseList(questionES.getQuestionCase()).stream()
                .limit(2)
                .collect(Collectors.toList());
        List<String> inputList = sampleCases.stream()
                .map(QuestionCase::getInput)
                .collect(Collectors.toCollection(ArrayList::new));
        List<String> outputList = sampleCases.stream()
                .map(QuestionCase::getOutput)
                .collect(Collectors.toCollection(ArrayList::new));

        if (CollectionUtil.isNotEmpty(customInputs)) {
            for (String customInput : customInputs) {
                if (StrUtil.isBlank(customInput)) {
                    continue;
                }
                inputList.add(customInput);
                outputList.add(null);
            }
        }

        if (CollectionUtil.isEmpty(inputList)) {
            throw new ServiceException(ResultCode.FAILED);
        }
        return new RunPayload(inputList, outputList);
    }

    private String codeConnect(String userCode, String mainFunc) {
        String targetCharacter = "}";
        int targetLastIndex = userCode.lastIndexOf(targetCharacter);
        if (targetLastIndex != -1) {
            return userCode.substring(0, targetLastIndex) + "\n" + mainFunc + "\n" + userCode.substring(targetLastIndex);
        }
        throw new ServiceException(ResultCode.FAILED);
    }

    private UserSubmit buildAcceptedSubmit(JudgeSubmitDTO judgeSubmitDTO) {
        UserSubmit userSubmit = new UserSubmit();
        userSubmit.setRequestId(judgeSubmitDTO.getRequestId());
        userSubmit.setUserId(judgeSubmitDTO.getUserId());
        userSubmit.setQuestionId(judgeSubmitDTO.getQuestionId());
        userSubmit.setExamId(judgeSubmitDTO.getExamId());
        userSubmit.setProgramType(judgeSubmitDTO.getProgramType());
        userSubmit.setUserCode(judgeSubmitDTO.getUserCode());
        userSubmit.setPass(QuestionResType.IN_JUDGE.getValue());
        userSubmit.setScore(0);
        userSubmit.setExeMessage("判题中");
        userSubmit.setRetryCount(0);
        userSubmit.setJudgeStatus(JudgeAsyncStatus.WAITING.getValue());
        userSubmit.setCreateBy(judgeSubmitDTO.getUserId());
        return userSubmit;
    }

    private UserSubmit getCurrentSubmit(Long userId,
                                        Long examId,
                                        Long questionId,
                                        String currentTime,
                                        String requestId) {
        if (StrUtil.isNotBlank(requestId)) {
            return userSubmitMapper.selectOne(new LambdaQueryWrapper<UserSubmit>()
                    .eq(UserSubmit::getRequestId, requestId)
                    .eq(UserSubmit::getUserId, userId));
        }
        return userSubmitMapper.selectCurrentUserSubmit(userId, examId, questionId, currentTime);
    }

    private UserSubmissionHistoryVO toSubmissionHistoryVO(UserSubmit userSubmit) {
        UserSubmissionHistoryVO historyVO = new UserSubmissionHistoryVO();
        historyVO.setSubmitId(userSubmit.getSubmitId());
        historyVO.setProgramType(userSubmit.getProgramType());
        historyVO.setPass(userSubmit.getPass());
        historyVO.setScore(userSubmit.getScore());
        historyVO.setExeMessage(userSubmit.getExeMessage());
        historyVO.setUseTime(userSubmit.getUseTime());
        historyVO.setUseMemory(userSubmit.getUseMemory());
        historyVO.setCreateTime(userSubmit.getCreateTime());
        historyVO.setUpdateTime(userSubmit.getUpdateTime());
        return historyVO;
    }

    private record RunPayload(List<String> inputList, List<String> outputList) {
    }
}
