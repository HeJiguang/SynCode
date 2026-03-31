package com.sintao.friend.domain.user.dto;

import lombok.Getter;
import lombok.Setter;

import java.util.List;

@Getter
@Setter
public class UserRunDTO {

    private Long questionId;

    private Long examId;

    private Integer programType;

    private String userCode;

    private List<String> customInputs;
}
