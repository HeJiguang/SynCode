package com.sintao.friend.domain.exam.vo;

import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;
import java.util.List;

@Getter
@Setter
public class ExamResultVO {
    private Long attemptId;
    private String status;
    private Integer totalScore;
    private Integer maxScore;
    private LocalDateTime releasedAt;
    private List<ExamGradeItemVO> items;
}
