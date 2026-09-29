package com.sintao.api.domain.dto;

import com.sintao.common.core.enums.JudgeTaskType;
import lombok.Getter;
import lombok.Setter;

import java.util.List;

@Getter
@Setter
public class JudgeSubmitDTO {

    private String requestId;

    private JudgeTaskType taskType;

    private Long userId;

    private Long examId;

    private Long attemptId;

    private Long versionQuestionId;

    private Long answerId;

    private Integer answerVersion;

    private String submitKind;

    private Integer programType;

    private Long questionId;

    private Integer difficulty;

    private Long timeLimit;

    private Long spaceLimit;

    private String userCode;

    private List<String> inputList;

    private List<String> outputList;
}
