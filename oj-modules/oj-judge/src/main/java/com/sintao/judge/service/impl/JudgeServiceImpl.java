package com.sintao.judge.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.alibaba.fastjson2.JSON;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.sintao.api.domain.UserExeResult;
import com.sintao.api.domain.dto.JudgeSubmitDTO;
import com.sintao.api.domain.vo.UserCodeRunVO;
import com.sintao.api.domain.vo.UserQuestionResultVO;
import com.sintao.api.domain.vo.UserRunCaseVO;
import com.sintao.common.core.constants.Constants;
import com.sintao.common.core.constants.JudgeConstants;
import com.sintao.common.core.domain.dto.JudgeResultPushDTO;
import com.sintao.common.core.enums.CodeRunStatus;
import com.sintao.common.core.enums.JudgeAsyncStatus;
import com.sintao.common.redis.service.JudgeResultPushService;
import com.sintao.judge.domain.SandBoxExecuteResult;
import com.sintao.judge.domain.UserSubmit;
import com.sintao.judge.mapper.UserSubmitMapper;
import com.sintao.judge.service.IJudgeService;
import com.sintao.judge.service.ISandboxPoolService;
import com.sintao.judge.service.ISandboxService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.UUID;

@Service
@Slf4j
public class JudgeServiceImpl implements IJudgeService {

    @Autowired
    private ISandboxService sandboxService;

    @Autowired
    private ISandboxPoolService sandboxPoolService;

    @Autowired
    private UserSubmitMapper userSubmitMapper;

    @Autowired
    private JudgeResultPushService judgeResultPushService;

    @Override
    public UserQuestionResultVO doJudgeJavaCode(JudgeSubmitDTO judgeSubmitDTO) {
        log.info("---- judge submit start ----");
        SandBoxExecuteResult sandBoxExecuteResult = executeJavaCode(judgeSubmitDTO);
        UserQuestionResultVO userQuestionResultVO = new UserQuestionResultVO();
        if (sandBoxExecuteResult != null && CodeRunStatus.SUCCEED.equals(sandBoxExecuteResult.getRunStatus())) {
            userQuestionResultVO = doJudge(judgeSubmitDTO, sandBoxExecuteResult, userQuestionResultVO);
        } else {
            userQuestionResultVO.setPass(Constants.FALSE);
            if (sandBoxExecuteResult != null) {
                userQuestionResultVO.setExeMessage(sandBoxExecuteResult.getExeMessage());
            } else {
                userQuestionResultVO.setExeMessage(CodeRunStatus.UNKNOWN_FAILED.getMsg());
            }
            userQuestionResultVO.setScore(JudgeConstants.ERROR_SCORE);
        }
        if (sandBoxExecuteResult != null) {
            userQuestionResultVO.setUseMemory(sandBoxExecuteResult.getUseMemory());
            userQuestionResultVO.setUseTime(sandBoxExecuteResult.getUseTime());
        }
        userQuestionResultVO.setExeMessage(resolveExeMessage(userQuestionResultVO));
        saveUserSubmit(judgeSubmitDTO, userQuestionResultVO);
        log.info("judge submit finished, result={}", userQuestionResultVO);
        return userQuestionResultVO;
    }

    @Override
    public UserCodeRunVO runJavaCode(JudgeSubmitDTO judgeSubmitDTO) {
        log.info("---- judge run start ----");
        SandBoxExecuteResult sandBoxExecuteResult = executeJavaCode(judgeSubmitDTO);
        UserCodeRunVO resultVO = new UserCodeRunVO();
        if (sandBoxExecuteResult == null) {
            resultVO.setRunStatus(CodeRunStatus.UNKNOWN_FAILED.name());
            resultVO.setExeMessage(CodeRunStatus.UNKNOWN_FAILED.getMsg());
            return resultVO;
        }

        resultVO.setRunStatus(sandBoxExecuteResult.getRunStatus().name());
        resultVO.setExeMessage(sandBoxExecuteResult.getExeMessage() != null
                ? sandBoxExecuteResult.getExeMessage()
                : sandBoxExecuteResult.getRunStatus().getMsg());
        resultVO.setUseMemory(sandBoxExecuteResult.getUseMemory());
        resultVO.setUseTime(sandBoxExecuteResult.getUseTime());

        if (!CodeRunStatus.SUCCEED.equals(sandBoxExecuteResult.getRunStatus())) {
            return resultVO;
        }

        List<String> inputList = judgeSubmitDTO.getInputList();
        List<String> expectedOutputList = judgeSubmitDTO.getOutputList();
        List<String> actualOutputList = sandBoxExecuteResult.getOutputList();
        List<UserRunCaseVO> caseResults = new ArrayList<>();
        for (int index = 0; index < inputList.size(); index++) {
            UserRunCaseVO caseVO = new UserRunCaseVO();
            caseVO.setInput(inputList.get(index));
            String expectedOutput = expectedOutputList != null && index < expectedOutputList.size()
                    ? expectedOutputList.get(index)
                    : null;
            String actualOutput = actualOutputList != null && index < actualOutputList.size()
                    ? actualOutputList.get(index)
                    : null;
            boolean custom = expectedOutput == null || expectedOutput.isBlank();
            caseVO.setExpectedOutput(expectedOutput);
            caseVO.setActualOutput(actualOutput);
            caseVO.setCustom(custom);
            caseVO.setPassed(custom ? null : expectedOutput.equals(actualOutput));
            caseResults.add(caseVO);
        }
        resultVO.setCaseResults(caseResults);
        return resultVO;
    }

    private SandBoxExecuteResult executeJavaCode(JudgeSubmitDTO judgeSubmitDTO) {
        try {
            return sandboxPoolService.exeJavaCode(
                    judgeSubmitDTO.getUserId(),
                    judgeSubmitDTO.getUserCode(),
                    judgeSubmitDTO.getInputList()
            );
        } catch (Exception e) {
            log.warn("Sandbox pool execution failed, fallback to standalone sandbox, requestId={}",
                    judgeSubmitDTO.getRequestId(), e);
            return sandboxService.exeJavaCode(
                    judgeSubmitDTO.getUserId(),
                    judgeSubmitDTO.getUserCode(),
                    judgeSubmitDTO.getInputList()
            );
        }
    }

    private UserQuestionResultVO doJudge(JudgeSubmitDTO judgeSubmitDTO,
                                         SandBoxExecuteResult sandBoxExecuteResult,
                                         UserQuestionResultVO userQuestionResultVO) {
        List<String> exeOutputList = sandBoxExecuteResult.getOutputList();
        List<String> outputList = judgeSubmitDTO.getOutputList();
        if (outputList.size() != exeOutputList.size()) {
            userQuestionResultVO.setScore(JudgeConstants.ERROR_SCORE);
            userQuestionResultVO.setPass(Constants.FALSE);
            userQuestionResultVO.setExeMessage(CodeRunStatus.NOT_ALL_PASSED.getMsg());
            return userQuestionResultVO;
        }
        List<UserExeResult> userExeResultList = new ArrayList<>();
        boolean passed = resultCompare(judgeSubmitDTO, exeOutputList, outputList, userExeResultList);
        return assembleUserQuestionResultVO(judgeSubmitDTO, sandBoxExecuteResult, userQuestionResultVO, userExeResultList, passed);
    }

    private UserQuestionResultVO assembleUserQuestionResultVO(JudgeSubmitDTO judgeSubmitDTO,
                                                              SandBoxExecuteResult sandBoxExecuteResult,
                                                              UserQuestionResultVO userQuestionResultVO,
                                                              List<UserExeResult> userExeResultList,
                                                              boolean passed) {
        userQuestionResultVO.setUserExeResultList(userExeResultList);
        if (!passed) {
            userQuestionResultVO.setPass(Constants.FALSE);
            userQuestionResultVO.setScore(JudgeConstants.ERROR_SCORE);
            userQuestionResultVO.setExeMessage(CodeRunStatus.NOT_ALL_PASSED.getMsg());
            return userQuestionResultVO;
        }
        if (sandBoxExecuteResult.getUseMemory() > resolveSpaceLimitBytes(judgeSubmitDTO.getSpaceLimit())) {
            userQuestionResultVO.setPass(Constants.FALSE);
            userQuestionResultVO.setScore(JudgeConstants.ERROR_SCORE);
            userQuestionResultVO.setExeMessage(CodeRunStatus.OUT_OF_MEMORY.getMsg());
            return userQuestionResultVO;
        }
        if (sandBoxExecuteResult.getUseTime() > judgeSubmitDTO.getTimeLimit()) {
            userQuestionResultVO.setPass(Constants.FALSE);
            userQuestionResultVO.setScore(JudgeConstants.ERROR_SCORE);
            userQuestionResultVO.setExeMessage(CodeRunStatus.OUT_OF_TIME.getMsg());
            return userQuestionResultVO;
        }
        userQuestionResultVO.setPass(Constants.TRUE);
        int score = judgeSubmitDTO.getDifficulty() * JudgeConstants.DEFAULT_SCORE;
        userQuestionResultVO.setScore(score);
        return userQuestionResultVO;
    }

    private boolean resultCompare(JudgeSubmitDTO judgeSubmitDTO,
                                  List<String> exeOutputList,
                                  List<String> outputList,
                                  List<UserExeResult> userExeResultList) {
        boolean passed = true;
        for (int index = 0; index < outputList.size(); index++) {
            String output = outputList.get(index);
            String exeOutput = exeOutputList.get(index);
            String input = judgeSubmitDTO.getInputList().get(index);
            UserExeResult userExeResult = new UserExeResult();
            userExeResult.setInput(input);
            userExeResult.setOutput(output);
            userExeResult.setExeOutput(exeOutput);
            userExeResultList.add(userExeResult);
            if (!output.equals(exeOutput)) {
                passed = false;
                log.info("input={}, expected={}, actual={}", input, output, exeOutput);
            }
        }
        return passed;
    }

    private void saveUserSubmit(JudgeSubmitDTO judgeSubmitDTO, UserQuestionResultVO userQuestionResultVO) {
        if (judgeSubmitDTO.getRequestId() != null) {
            String caseJudgeRes = JSON.toJSONString(userQuestionResultVO.getUserExeResultList());
            LocalDateTime finishTime = LocalDateTime.now();
            userSubmitMapper.update(null, new UpdateWrapper<UserSubmit>()
                    .eq("request_id", judgeSubmitDTO.getRequestId())
                    .set("pass", userQuestionResultVO.getPass())
                    .set("score", userQuestionResultVO.getScore())
                    .set("exe_message", userQuestionResultVO.getExeMessage())
                    .set("case_judge_res", caseJudgeRes)
                    .set("use_time", userQuestionResultVO.getUseTime())
                    .set("use_memory", userQuestionResultVO.getUseMemory())
                    .set("judge_status", JudgeAsyncStatus.SUCCESS.getValue())
                    .set("finish_time", finishTime)
                    .set("update_by", judgeSubmitDTO.getUserId()));
            JudgeResultPushDTO pushDTO = new JudgeResultPushDTO();
            pushDTO.setRequestId(judgeSubmitDTO.getRequestId());
            pushDTO.setUserId(judgeSubmitDTO.getUserId());
            pushDTO.setAsyncStatus(JudgeAsyncStatus.SUCCESS.getValue());
            pushDTO.setPass(userQuestionResultVO.getPass());
            pushDTO.setExeMessage(userQuestionResultVO.getExeMessage());
            pushDTO.setCaseJudgeRes(caseJudgeRes);
            pushDTO.setScore(userQuestionResultVO.getScore());
            pushDTO.setUseTime(userQuestionResultVO.getUseTime());
            pushDTO.setUseMemory(userQuestionResultVO.getUseMemory());
            pushDTO.setFinishTime(finishTime);
            judgeResultPushService.publishFinalResult(pushDTO);
            return;
        }
        UserSubmit userSubmit = new UserSubmit();
        BeanUtil.copyProperties(userQuestionResultVO, userSubmit);
        userSubmit.setUserId(judgeSubmitDTO.getUserId());
        userSubmit.setQuestionId(judgeSubmitDTO.getQuestionId());
        userSubmit.setExamId(judgeSubmitDTO.getExamId());
        userSubmit.setProgramType(judgeSubmitDTO.getProgramType());
        userSubmit.setUserCode(judgeSubmitDTO.getUserCode());
        userSubmit.setCaseJudgeRes(JSON.toJSONString(userQuestionResultVO.getUserExeResultList()));
        userSubmit.setRequestId(UUID.randomUUID().toString());
        userSubmit.setCreateBy(judgeSubmitDTO.getUserId());
        userSubmitMapper.delete(new LambdaQueryWrapper<UserSubmit>()
                .eq(UserSubmit::getUserId, judgeSubmitDTO.getUserId())
                .eq(UserSubmit::getQuestionId, judgeSubmitDTO.getQuestionId())
                .isNull(judgeSubmitDTO.getExamId() == null, UserSubmit::getExamId)
                .eq(judgeSubmitDTO.getExamId() != null, UserSubmit::getExamId, judgeSubmitDTO.getExamId()));
        userSubmitMapper.insert(userSubmit);
    }

    private String resolveExeMessage(UserQuestionResultVO userQuestionResultVO) {
        if (userQuestionResultVO.getExeMessage() != null && !userQuestionResultVO.getExeMessage().isBlank()) {
            return userQuestionResultVO.getExeMessage();
        }
        if (Objects.equals(userQuestionResultVO.getPass(), Constants.TRUE)) {
            return CodeRunStatus.SUCCEED.getMsg();
        }
        return CodeRunStatus.UNKNOWN_FAILED.getMsg();
    }

    private long resolveSpaceLimitBytes(Long spaceLimit) {
        if (spaceLimit == null || spaceLimit <= 0) {
            return 0L;
        }
        return spaceLimit * 1024L;
    }
}
