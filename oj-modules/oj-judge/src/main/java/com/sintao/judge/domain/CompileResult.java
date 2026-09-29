package com.sintao.judge.domain;

import lombok.Data;

@Data
public class CompileResult {

    private boolean compiled;  //编译是否成功

    private boolean timedOut;

    private String exeMessage;  //编译输出信息 （错误信息）
}

