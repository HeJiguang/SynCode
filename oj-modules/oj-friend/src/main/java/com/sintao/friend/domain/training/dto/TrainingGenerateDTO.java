package com.sintao.friend.domain.training.dto;

import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class TrainingGenerateDTO {

    private String prompt;

    private String targetDirection;

    private Integer preferredCount;

    private Long basedOnExamId;

    private String sourceType;
}
