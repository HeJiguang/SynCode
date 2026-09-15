package com.sintao.friend.domain.exam;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;

@Getter
@Setter
@TableName("tb_exam_answer")
public class ExamAnswer {
    @TableId(value = "answer_id", type = IdType.ASSIGN_ID)
    private Long answerId;
    private Long attemptId;
    private Long versionQuestionId;
    private String answerType;
    private String languageCode;
    private String answerContent;
    private String contentHash;
    private Integer answerVersion;
    private LocalDateTime savedTime;
    private LocalDateTime frozenTime;
    private Long latestSubmitId;
    private Long latestAcceptedSubmitId;
    private LocalDateTime createTime;
    private LocalDateTime updateTime;
}
