package com.sintao.system.domain.exam.vo;

import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;

@Getter
@Setter
public class ExamEvidenceEventVO {
    private String category;
    private String eventType;
    private LocalDateTime serverTime;
    private LocalDateTime clientObservedTime;
    private Integer riskPoints;
    private String metadataJson;
}
