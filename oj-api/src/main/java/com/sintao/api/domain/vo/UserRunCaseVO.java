package com.sintao.api.domain.vo;

import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class UserRunCaseVO {

    private String input;

    private String expectedOutput;

    private String actualOutput;

    private Boolean passed;

    private Boolean custom;
}
