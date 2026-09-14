package com.sintao.friend.domain.exam;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;

@Getter
@Setter
@TableName("tb_exam_audit_event")
public class ExamAuditEvent {
    @TableId(value = "audit_event_id", type = IdType.ASSIGN_ID)
    private Long auditEventId;
    private Long examId;
    private Long attemptId;
    private Long actorId;
    private String actorType;
    private String action;
    private String requestId;
    private Integer resultCode;
    private String metadataJson;
    private LocalDateTime serverTime;
}
