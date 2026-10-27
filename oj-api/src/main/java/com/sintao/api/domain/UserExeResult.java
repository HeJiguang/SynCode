package com.sintao.api.domain;

import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class UserExeResult {

    private String caseId;

    private Boolean passed;

    private Boolean custom;

    private String message;

    private Boolean truncated;

    private String input;

    private String output;   //鏈熸湜杈撳嚭

    private String exeOutput; //瀹為檯杈撳嚭
}

