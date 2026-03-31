package com.sintao.judge.controller;

import com.sintao.api.domain.dto.JudgeSubmitDTO;
import com.sintao.api.domain.vo.UserCodeRunVO;
import com.sintao.api.domain.vo.UserQuestionResultVO;
import com.sintao.common.core.controller.BaseController;
import com.sintao.common.core.domain.R;
import com.sintao.judge.service.IJudgeService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/judge")
@Slf4j
public class JudgeController extends BaseController {

    @Autowired
    private IJudgeService judgeService;

    @PostMapping("/doJudgeJavaCode")
    public R<UserQuestionResultVO> doJudgeJavaCode(@RequestBody JudgeSubmitDTO judgeSubmitDTO) {
        return R.ok(judgeService.doJudgeJavaCode(judgeSubmitDTO));
    }

    @PostMapping("/runJavaCode")
    public R<UserCodeRunVO> runJavaCode(@RequestBody JudgeSubmitDTO judgeSubmitDTO) {
        return R.ok(judgeService.runJavaCode(judgeSubmitDTO));
    }
}

