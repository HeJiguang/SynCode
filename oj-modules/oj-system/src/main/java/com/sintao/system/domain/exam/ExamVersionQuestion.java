package com.sintao.system.domain.exam;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;

@Getter
@Setter
@TableName("tb_exam_version_question")
public class ExamVersionQuestion {

    @TableId(value = "version_question_id", type = IdType.ASSIGN_ID)
    private Long versionQuestionId;
    private Long versionId;
    private Long questionId;
    private Integer questionOrder;
    private Integer score;
    private Integer requiredFlag;
    private String questionType;
    private String title;
    private String content;
    private Long timeLimit;
    private Long spaceLimit;
    private String questionCase;
    private String defaultCode;
    private String mainFuc;
    private String allowedLanguagesJson;
    private String starterCodeJson;
    private String judgeConfigJson;
    private LocalDateTime sourceUpdateTime;
    private String contentHash;
}
