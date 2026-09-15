package com.sintao.system.domain.exam.vo;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.databind.annotation.JsonSerialize;
import com.fasterxml.jackson.databind.ser.std.ToStringSerializer;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;

@Getter
@Setter
public class ExamPublicationVO {

    @JsonSerialize(using = ToStringSerializer.class)
    private Long versionId;
    private Integer versionNo;
    private String contentHash;
    @JsonSerialize(using = ToStringSerializer.class)
    private Long publishedBy;
    @JsonFormat(pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")
    private LocalDateTime publishedAt;
    private boolean replayed;
}
