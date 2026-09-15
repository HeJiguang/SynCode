package com.sintao.system.domain.exam;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;

@Getter
@Setter
@TableName("tb_exam_command")
public class ExamCommand {

    @TableId(value = "command_id", type = IdType.ASSIGN_ID)
    private Long commandId;
    private String commandType;
    private Long actorId;
    private String idempotencyKey;
    private String requestHash;
    private String targetType;
    private Long targetId;
    private Integer status;
    private Integer resultCode;
    private String responseJson;
    private LocalDateTime expiresTime;
    private LocalDateTime createTime;
    private LocalDateTime updateTime;
}
