package com.sintao.system.domain.exam.vo;

import com.sintao.system.domain.question.vo.QuestionVO;
import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.databind.annotation.JsonSerialize;
import com.fasterxml.jackson.databind.ser.std.ToStringSerializer;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;
import java.util.List;

@Getter
@Setter
@JsonInclude(JsonInclude.Include.NON_NULL)
public class ExamDetailVO {

    @JsonSerialize(using = ToStringSerializer.class)
    private Long examId;

    private String title;

    private String description;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime startTime;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime latestStartTime;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime endTime;

    private Integer durationMinutes;

    private String timezone;

    private Integer maxFormalSubmissions;

    private String resultReleasePolicy;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime resultReleaseTime;

    @JsonSerialize(using = ToStringSerializer.class)
    private Long currentVersionId;

    private Integer versionNo;

    private Integer rowVersion;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime publishedTime;

    private Integer status;

    private List<String> allowedActions;

    private List<QuestionVO> examQuestionList;
}

