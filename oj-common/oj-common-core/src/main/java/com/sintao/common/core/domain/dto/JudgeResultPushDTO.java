package com.sintao.common.core.domain.dto;

import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;

@Getter
@Setter
public class JudgeResultPushDTO {

    private String requestId;

    private Long userId;

    private Integer asyncStatus;

    private Integer pass;

    private String exeMessage;

    private String caseJudgeRes;

    private Integer score;

    private Long useTime;

    private Long useMemory;

    private String lastError;

    private LocalDateTime finishTime;
}
