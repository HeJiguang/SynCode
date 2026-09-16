package com.sintao.system.domain.question.es;

import lombok.Getter;
import lombok.Setter;
import org.springframework.data.annotation.Id;
import org.springframework.data.elasticsearch.annotations.DateFormat;
import org.springframework.data.elasticsearch.annotations.Document;
import org.springframework.data.elasticsearch.annotations.Field;
import org.springframework.data.elasticsearch.annotations.FieldType;

import java.time.LocalDateTime;

@Getter
@Setter
@Document(indexName = "idx_question")
public class QuestionES {

    @Id
    @Field(type = FieldType.Long)
    private Long questionId;

    @Field(type = FieldType.Text, analyzer = "standard", searchAnalyzer = "standard")
    private String title;

    @Field(type = FieldType.Byte)
    private Integer difficulty;

    @Field(type = FieldType.Keyword)
    private String algorithmTag;

    @Field(type = FieldType.Text, analyzer = "standard", searchAnalyzer = "standard")
    private String knowledgeTags;

    @Field(type = FieldType.Integer)
    private Integer estimatedMinutes;

    @Field(type = FieldType.Byte)
    private Integer trainingEnabled;

    @Field(type = FieldType.Keyword)
    private String questionType;

    @Field(type = FieldType.Long)
    private Long timeLimit;

    @Field(type = FieldType.Long)
    private Long spaceLimit;

    @Field(type = FieldType.Text, analyzer = "standard", searchAnalyzer = "standard")
    private String content;

    @Field(type = FieldType.Text)
    private String questionCase;

    @Field(type = FieldType.Text)
    private String mainFuc;

    @Field(type = FieldType.Text)
    private String defaultCode;

    @Field(type = FieldType.Date, format = DateFormat.date_hour_minute_second)
    private LocalDateTime createTime;
}

