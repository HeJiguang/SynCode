package com.sintao.system.domain.exam;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;

@Getter
@Setter
@TableName("tb_exam_answer")
public class ExamAnswer {
    @TableId(value = "answer_id", type = IdType.ASSIGN_ID)
    private Long answerId;
    private Long attemptId;
    private LocalDateTime frozenTime;
    private LocalDateTime updateTime;
}
