package com.sintao.system.domain.notice.dto;

import com.sintao.common.core.domain.PageQueryDTO;
import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class NoticeQueryDTO extends PageQueryDTO {

    private String title;

    private Integer status;
}
