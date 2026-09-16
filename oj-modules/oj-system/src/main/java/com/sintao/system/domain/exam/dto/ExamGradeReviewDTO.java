package com.sintao.system.domain.exam.dto;

import lombok.Getter;
import lombok.Setter;

import java.util.List;

@Getter
@Setter
public class ExamGradeReviewDTO {
    private List<Item> items;

    @Getter
    @Setter
    public static class Item {
        private Long versionQuestionId;
        private Integer awardedScore;
        private String feedback;
    }
}
