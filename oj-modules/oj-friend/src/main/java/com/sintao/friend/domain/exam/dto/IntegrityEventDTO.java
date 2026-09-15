package com.sintao.friend.domain.exam.dto;

import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;
import java.util.Map;

@Getter
@Setter
public class IntegrityEventDTO {
    private Long clientSequence;
    private String eventType;
    private LocalDateTime clientObservedTime;
    private Map<String, Object> metadata;
}
