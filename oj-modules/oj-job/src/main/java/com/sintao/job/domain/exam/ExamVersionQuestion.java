package com.sintao.job.domain.exam;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
@TableName("tb_exam_version_question")
public class ExamVersionQuestion {
    @TableId(value = "version_question_id", type = IdType.ASSIGN_ID)
    private Long versionQuestionId;
    private Long versionId;
    private Integer questionOrder;
    private Integer score;
}
