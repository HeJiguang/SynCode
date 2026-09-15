package com.sintao.job.domain.exam;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;

@Getter
@Setter
@TableName("tb_exam_grade_item")
public class ExamGradeItem {
    @TableId(value = "grade_item_id", type = IdType.ASSIGN_ID)
    private Long gradeItemId;
    private Long gradeId;
    private Long versionQuestionId;
    private Long submitId;
    private Integer awardedScore;
    private Integer maxScore;
    private String gradingMode;
    private Long createBy;
    private LocalDateTime createTime;
}
