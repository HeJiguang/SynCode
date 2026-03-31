package com.sintao.system.domain.notice.dto;

import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class NoticeAddDTO {

    private String title;

    private String content;

    private String category;

    private Integer isPublic;

    private Integer isPinned;
}
