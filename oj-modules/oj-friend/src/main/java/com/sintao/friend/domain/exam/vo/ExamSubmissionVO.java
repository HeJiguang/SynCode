package com.sintao.friend.domain.exam.vo;

import com.fasterxml.jackson.databind.annotation.JsonSerialize;
import com.fasterxml.jackson.databind.ser.std.ToStringSerializer;
import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class ExamSubmissionVO {
    @JsonSerialize(using = ToStringSerializer.class)
    private Long submitId;
    private String requestId;
    private String status;
    private String submitKind;
    private Integer remainingFormalSubmissions;
    private boolean replayed;
}
