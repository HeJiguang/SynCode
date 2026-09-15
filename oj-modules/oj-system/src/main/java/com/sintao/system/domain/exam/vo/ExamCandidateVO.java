package com.sintao.system.domain.exam.vo;

import com.fasterxml.jackson.databind.annotation.JsonSerialize;
import com.fasterxml.jackson.databind.ser.std.ToStringSerializer;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;

@Getter
@Setter
public class ExamCandidateVO {
    @JsonSerialize(using = ToStringSerializer.class)
    private Long userId;
    @JsonSerialize(using = ToStringSerializer.class)
    private Long attemptId;
    private String nickName;
    private String email;
    private boolean authorized;
    private String authorizationSource;
    private String attemptStatus;
    private LocalDateTime startedAt;
    private LocalDateTime lastActiveAt;
    private Integer riskLevel;
}
