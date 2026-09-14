package com.sintao.friend.domain.exam.vo;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.databind.annotation.JsonSerialize;
import com.fasterxml.jackson.databind.ser.std.ToStringSerializer;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;

@Getter
@Setter
public class ExamAnswerVO {
    @JsonSerialize(using = ToStringSerializer.class)
    private Long answerId;
    @JsonSerialize(using = ToStringSerializer.class)
    private Long versionQuestionId;
    private String answerType;
    private String language;
    private String content;
    private String contentHash;
    private Integer answerVersion;
    @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")
    private LocalDateTime savedAt;
    private boolean frozen;
}
