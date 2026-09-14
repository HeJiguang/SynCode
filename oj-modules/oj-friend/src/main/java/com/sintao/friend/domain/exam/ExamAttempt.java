package com.sintao.friend.domain.exam;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;

@Getter
@Setter
@TableName("tb_exam_attempt")
public class ExamAttempt {
    @TableId(value = "attempt_id", type = IdType.ASSIGN_ID)
    private Long attemptId;
    private Long examId;
    private Long versionId;
    private Long userId;
    private Integer status;
    private Integer rowVersion;
    private LocalDateTime startedTime;
    private LocalDateTime deadlineTime;
    private LocalDateTime lastActiveTime;
    private LocalDateTime submittedTime;
    private LocalDateTime finalizedTime;
    private String finalizationReason;
    private String finalizationKey;
    private String firstIpHash;
    private String latestIpHash;
    private String userAgentHash;
    private String currentSessionId;
    private Integer riskLevel;
    private LocalDateTime createTime;
    private LocalDateTime updateTime;
}
