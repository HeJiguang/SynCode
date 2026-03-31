package com.sintao.system.domain.notice;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.sintao.common.core.domain.BaseEntity;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;

@Getter
@Setter
@TableName("tb_notice")
public class Notice extends BaseEntity {

    @TableId(value = "NOTICE_ID", type = IdType.ASSIGN_ID)
    private Long noticeId;

    private String title;

    private String content;

    private String category;

    private Integer isPublic;

    private Integer isPinned;

    private Integer status;

    private LocalDateTime publishTime;
}
