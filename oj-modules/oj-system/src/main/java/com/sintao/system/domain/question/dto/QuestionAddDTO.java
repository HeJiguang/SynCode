package com.sintao.system.domain.question.dto;

import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class QuestionAddDTO {

    private String title;

    private Integer difficulty;

    private String algorithmTag;

    private String knowledgeTags;

    private Integer estimatedMinutes;

    private Integer trainingEnabled;

    private String questionType;

    private String answerConfigJson;

    private String gradingConfigJson;

    private Long timeLimit;

    private Long spaceLimit;

    private String content;

    private String questionCase;

    private String defaultCode;

    private String mainFuc;
}

