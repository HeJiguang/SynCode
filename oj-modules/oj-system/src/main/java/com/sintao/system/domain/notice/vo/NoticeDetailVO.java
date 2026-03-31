package com.sintao.system.domain.notice.vo;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.databind.annotation.JsonSerialize;
import com.fasterxml.jackson.databind.ser.std.ToStringSerializer;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;

@Getter
@Setter
public class NoticeDetailVO {

    @JsonSerialize(using = ToStringSerializer.class)
    private Long noticeId;

    private String title;

    private String content;

    private String category;

    private Integer isPublic;

    private Integer isPinned;

    private Integer status;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime publishTime;
}
