package com.sintao.api.domain.vo;

import lombok.Getter;
import lombok.Setter;

import java.util.List;

@Getter
@Setter
public class UserCodeRunVO {

    private String runStatus;

    private String exeMessage;

    private Long useMemory;

    private Long useTime;

    private List<UserRunCaseVO> caseResults;
}
