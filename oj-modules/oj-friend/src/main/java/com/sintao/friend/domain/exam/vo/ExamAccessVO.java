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
public class ExamAccessVO {
    @JsonSerialize(using = ToStringSerializer.class)
    private Long examId;
    private String title;
    private String description;
    private String status;
    private boolean authorized;
    private boolean canStart;
    private boolean canResume;
    @JsonSerialize(using = ToStringSerializer.class)
    private Long attemptId;
    @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")
    private LocalDateTime serverNow;
    @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")
    private LocalDateTime startAt;
    @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")
    private LocalDateTime latestStartAt;
    @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")
    private LocalDateTime endAt;
    private Integer durationMinutes;
    private String timezone;
    private String privacyNotice;
    private List<String> allowedActions;
}
