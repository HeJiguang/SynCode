package com.sintao.system.domain.exam;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;

@Getter
@Setter
@TableName("tb_integrity_event")
public class IntegrityEvent {
    @TableId(value = "integrity_event_id", type = IdType.ASSIGN_ID)
    private Long integrityEventId;
    private Long attemptId;
    private String sessionId;
    private Long clientSequence;
    private String eventType;
    private LocalDateTime clientObservedTime;
    private LocalDateTime serverReceivedTime;
    private String metadataJson;
    private Integer riskPoints;
}
