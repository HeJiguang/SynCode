package com.sintao.friend.domain.exam.vo;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.databind.annotation.JsonSerialize;
import com.fasterxml.jackson.databind.ser.std.ToStringSerializer;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;
import java.util.List;

@Getter
@Setter
public class ExamAttemptVO {
    @JsonSerialize(using = ToStringSerializer.class)
    private Long attemptId;
    @JsonSerialize(using = ToStringSerializer.class)
    private Long examId;
    @JsonSerialize(using = ToStringSerializer.class)
    private Long versionId;
    private String title;
    private String description;
    private String status;
    @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")
    private LocalDateTime serverNow;
    @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")
    private LocalDateTime startedAt;
    @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")
    private LocalDateTime deadlineAt;
    @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")
    private LocalDateTime submittedAt;
    private String finalizationReason;
    private String timezone;
    private boolean replayed;
    private List<TrustedExamQuestionVO> questions;
    private List<ExamAnswerVO> answers;
}
