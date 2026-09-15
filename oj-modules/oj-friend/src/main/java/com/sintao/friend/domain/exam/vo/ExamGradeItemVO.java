package com.sintao.friend.domain.exam.vo;

import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class ExamGradeItemVO {
    private Long versionQuestionId;
    private Integer awardedScore;
    private Integer maxScore;
    private String gradingMode;
}
