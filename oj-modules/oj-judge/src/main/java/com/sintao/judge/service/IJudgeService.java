package com.sintao.judge.service;

import com.sintao.api.domain.dto.JudgeSubmitDTO;
import com.sintao.api.domain.vo.UserCodeRunVO;
import com.sintao.api.domain.vo.UserQuestionResultVO;

public interface IJudgeService {
    UserQuestionResultVO doJudgeJavaCode(JudgeSubmitDTO judgeSubmitDTO);

    UserCodeRunVO runJavaCode(JudgeSubmitDTO judgeSubmitDTO);
}

