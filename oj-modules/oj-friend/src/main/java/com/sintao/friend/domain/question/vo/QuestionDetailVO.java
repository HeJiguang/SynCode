package com.sintao.friend.domain.question.vo;

import lombok.Getter;
import lombok.Setter;

import java.util.List;

@Getter
@Setter
public class QuestionDetailVO extends QuestionVO {

    private Long timeLimit;

    private Long spaceLimit;

    private String algorithmTag;

    private String knowledgeTags;

    private Integer estimatedMinutes;

    private Integer trainingEnabled;

    private String content;

    private String defaultCode;

    private List<QuestionCaseVO> exampleCases;
}
