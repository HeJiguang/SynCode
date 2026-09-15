package com.sintao.system.domain.exam;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.sintao.common.core.domain.BaseEntity;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;

@Getter
@Setter
@TableName("tb_user_exam")
public class UserExam extends BaseEntity {
    @TableId(value = "user_exam_id", type = IdType.ASSIGN_ID)
    private Long userExamId;
    private Long examId;
    private Long userId;
    private Integer authorizationStatus;
    private String authorizationSource;
    private Long revokedBy;
    private LocalDateTime revokedTime;
    private String revokeReason;
    private Integer score;
    private Integer examRank;
}
