package com.sintao.job.domain.exam;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;

@Getter
@Setter
@TableName("tb_exam_grade")
public class ExamGrade {
    @TableId(value = "grade_id", type = IdType.ASSIGN_ID)
    private Long gradeId;
    private Long attemptId;
    private Integer revision;
    private Integer status;
    private Integer totalScore;
    private Integer maxScore;
    private String calculationSource;
    private Integer currentFlag;
    private LocalDateTime calculatedTime;
    private LocalDateTime releasedTime;
    private Long createBy;
    private LocalDateTime createTime;
    private Long updateBy;
    private LocalDateTime updateTime;
}
