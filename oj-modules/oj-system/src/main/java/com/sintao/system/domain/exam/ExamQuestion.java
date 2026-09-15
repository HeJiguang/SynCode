package com.sintao.system.domain.exam;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.sintao.common.core.domain.BaseEntity;
import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
@TableName("tb_exam_question")
public class ExamQuestion extends BaseEntity {

    @TableId(value = "EXAM_QUESTION_ID", type = IdType.ASSIGN_ID)
    private Long examQuestionId;

    private Long examId;

    private Long questionId;

    private Integer questionOrder;

    private Integer score;

    private Integer requiredFlag;

    private String questionType;
}
