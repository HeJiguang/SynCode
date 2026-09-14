package com.sintao.friend.domain.user;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.sintao.common.core.domain.BaseEntity;
import com.fasterxml.jackson.databind.annotation.JsonSerialize;
import com.fasterxml.jackson.databind.ser.std.ToStringSerializer;
import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
@TableName("tb_user_exam")
public class UserExam extends BaseEntity {

	@JsonSerialize(using = ToStringSerializer.class)
	@TableId(value = "USER_EXAM_ID", type = IdType.ASSIGN_ID)
	private Long userExamId;

	@JsonSerialize(using = ToStringSerializer.class)
	private Long examId;

	@JsonSerialize(using = ToStringSerializer.class)
	private Long userId;

	private Integer authorizationStatus;

	private String authorizationSource;

	private Long revokedBy;

	private java.time.LocalDateTime revokedTime;

	private String revokeReason;

	private Integer score;

	private Integer examRank;
}
