package com.sintao.system.domain.exam.vo;

import com.fasterxml.jackson.databind.annotation.JsonSerialize;
import com.fasterxml.jackson.databind.ser.std.ToStringSerializer;
import lombok.Getter;
import lombok.Setter;

import java.util.List;

@Getter
@Setter
public class ExamGradeReviewVO {
    @JsonSerialize(using = ToStringSerializer.class)
    private Long attemptId;
    private String candidateName;
    private String status;
    private Integer totalScore;
    private Integer maxScore;
    private List<Item> items;

    @Getter
    @Setter
    public static class Item {
        @JsonSerialize(using = ToStringSerializer.class)
        private Long versionQuestionId;
        private Integer questionOrder;
        private String title;
        private String questionType;
        private String answerType;
        private String language;
        private String answerContent;
        private String gradingRubric;
        private Integer awardedScore;
        private Integer maxScore;
        private String gradingMode;
        private String feedback;
    }
}
