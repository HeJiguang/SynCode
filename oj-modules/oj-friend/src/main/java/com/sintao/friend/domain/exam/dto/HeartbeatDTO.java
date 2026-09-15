package com.sintao.friend.domain.exam.dto;

import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class HeartbeatDTO {
    private String sessionId;
    private Boolean takeover;
}
