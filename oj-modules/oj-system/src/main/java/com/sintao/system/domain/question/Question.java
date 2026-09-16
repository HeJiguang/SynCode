package com.sintao.system.domain.question;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.sintao.common.core.domain.BaseEntity;
import lombok.Getter;
import lombok.Setter;

@TableName("tb_question")
@Getter
@Setter
public class Question extends BaseEntity {

    @TableId(type = IdType.ASSIGN_ID)
    private Long questionId;

    private String title;

    private Integer difficulty;

    private String algorithmTag;

    private String knowledgeTags;

    private Integer estimatedMinutes;

    private Integer trainingEnabled;

    private String questionType;

    private String answerConfigJson;

    private String gradingConfigJson;

    private Long timeLimit;

    private Long spaceLimit;

    private String content;

    private String questionCase;

    private String defaultCode;

    private String mainFuc;
}

