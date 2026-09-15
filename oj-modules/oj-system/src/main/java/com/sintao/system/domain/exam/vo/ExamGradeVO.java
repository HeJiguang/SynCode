package com.sintao.system.domain.exam.vo;

import com.fasterxml.jackson.databind.annotation.JsonSerialize;
import com.fasterxml.jackson.databind.ser.std.ToStringSerializer;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;

@Getter
@Setter
public class ExamGradeVO {
    @JsonSerialize(using = ToStringSerializer.class)
    private Long gradeId;
    @JsonSerialize(using = ToStringSerializer.class)
    private Long attemptId;
    @JsonSerialize(using = ToStringSerializer.class)
    private Long userId;
    private String nickName;
    private String status;
    private Integer totalScore;
    private Integer maxScore;
    private Integer riskLevel;
    private LocalDateTime calculatedAt;
    private LocalDateTime releasedAt;
}
