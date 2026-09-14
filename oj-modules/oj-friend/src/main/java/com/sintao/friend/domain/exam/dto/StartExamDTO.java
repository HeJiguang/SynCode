package com.sintao.friend.domain.exam.dto;

import lombok.Getter;
import lombok.Setter;

import java.util.Map;

@Getter
@Setter
public class StartExamDTO {
    private String sessionId;
    private Map<String, String> client;
}
