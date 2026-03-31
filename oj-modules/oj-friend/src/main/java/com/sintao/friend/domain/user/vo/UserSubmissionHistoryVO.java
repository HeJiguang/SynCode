package com.sintao.friend.domain.user.vo;

import com.fasterxml.jackson.databind.annotation.JsonSerialize;
import com.fasterxml.jackson.databind.ser.std.ToStringSerializer;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;

@Getter
@Setter
public class UserSubmissionHistoryVO {

    @JsonSerialize(using = ToStringSerializer.class)
    private Long submitId;

    private Integer programType;

    private Integer pass;

    private Integer score;

    private String exeMessage;

    private Long useTime;

    private Long useMemory;

    private LocalDateTime createTime;

    private LocalDateTime updateTime;
}
