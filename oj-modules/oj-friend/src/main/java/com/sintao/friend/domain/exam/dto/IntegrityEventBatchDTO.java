package com.sintao.friend.domain.exam.dto;

import lombok.Getter;
import lombok.Setter;

import java.util.List;

@Getter
@Setter
public class IntegrityEventBatchDTO {
    private String sessionId;
    private List<IntegrityEventDTO> events;
}
