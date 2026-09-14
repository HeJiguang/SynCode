package com.sintao.system.domain.exam.dto;

import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class ExamQuestionItemDTO {

    private Long questionId;

    private Integer questionOrder;

    private Integer score;

    private Boolean required;

    private String questionType;
}
