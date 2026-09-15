package com.sintao.friend.domain.exam.vo;

import com.fasterxml.jackson.databind.annotation.JsonSerialize;
import com.fasterxml.jackson.databind.ser.std.ToStringSerializer;
import lombok.Getter;
import lombok.Setter;

import java.util.List;
import java.util.Map;

@Getter
@Setter
public class TrustedExamQuestionVO {
    @JsonSerialize(using = ToStringSerializer.class)
    private Long versionQuestionId;
    private Integer questionOrder;
    private Integer score;
    private boolean required;
    private String questionType;
    private String title;
    private String content;
    private Long timeLimit;
    private Long spaceLimit;
    private List<String> allowedLanguages;
    private Map<String, String> starterCode;
}
