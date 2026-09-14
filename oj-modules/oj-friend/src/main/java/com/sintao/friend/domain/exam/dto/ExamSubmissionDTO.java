package com.sintao.friend.domain.exam.dto;

import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class ExamSubmissionDTO {
    private Long versionQuestionId;
    private Integer answerVersion;
    private String submitKind;
}
