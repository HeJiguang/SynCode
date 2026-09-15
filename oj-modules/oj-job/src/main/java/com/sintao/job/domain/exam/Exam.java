package com.sintao.job.domain.exam;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.sintao.common.core.domain.BaseEntity;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;

@Getter
@Setter
@TableName("tb_exam")
public class Exam extends BaseEntity {
    @TableId(value = "exam_id", type = IdType.ASSIGN_ID)
    private Long examId;
    private String title;
    private LocalDateTime startTime;
    private LocalDateTime endTime;
    private String resultReleasePolicy;
    private LocalDateTime resultReleaseTime;
    private Integer rowVersion;
    private LocalDateTime finishedTime;
    private LocalDateTime resultReleasedTime;
    private Integer status;
}
