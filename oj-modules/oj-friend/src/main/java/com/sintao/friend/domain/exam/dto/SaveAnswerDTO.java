package com.sintao.friend.domain.exam.dto;

import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class SaveAnswerDTO {
    private Integer expectedVersion;
    private String answerType;
    private String language;
    private String content;
    private String contentHash;
}
