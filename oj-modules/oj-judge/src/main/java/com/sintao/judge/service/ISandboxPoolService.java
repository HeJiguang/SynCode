package com.sintao.judge.service;

import com.sintao.judge.domain.SandBoxExecuteResult;

import java.util.List;

public interface ISandboxPoolService {
    SandBoxExecuteResult executeCode(Integer programType, Long userId, String userCode, List<String> inputList);
}

