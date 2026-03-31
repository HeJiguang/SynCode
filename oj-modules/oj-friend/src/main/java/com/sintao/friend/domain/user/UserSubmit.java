package com.sintao.friend.domain.user;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.sintao.common.core.domain.BaseEntity;
import com.fasterxml.jackson.databind.annotation.JsonSerialize;
import com.fasterxml.jackson.databind.ser.std.ToStringSerializer;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.LocalDateTime;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@TableName("tb_user_submit")
public class UserSubmit extends BaseEntity {
    
	@TableId(value = "SUBMIT_ID", type = IdType.ASSIGN_ID)
	@JsonSerialize(using = ToStringSerializer.class)
	private Long submitId;

	private Long userId; //唯一确定用户     2001/2002

	private Long questionId;  //唯一确定题目  100      100     102

	private Long examId;   //唯一确定竞赛      1       2          3   4    null

	private Integer programType;

	private String userCode;

	private Integer pass;

	private Integer score;

	private String exeMessage;

	private String caseJudgeRes;

	private Long useTime;

	private Long useMemory;

	private String requestId;

	private Integer judgeStatus;

	private Integer retryCount;

	private String lastError;

	private LocalDateTime finishTime;
}
