package com.sintao.api;


import com.sintao.api.domain.dto.JudgeSubmitDTO;
import com.sintao.api.domain.vo.UserCodeRunVO;
import com.sintao.api.domain.vo.UserQuestionResultVO;
import com.sintao.common.core.constants.Constants;
import com.sintao.common.core.domain.R;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;

@FeignClient(contextId = "RemoteJudgeService", value = Constants.JUDGE_SERVICE)
public interface RemoteJudgeService {

    @PostMapping("/judge/doJudgeJavaCode")
    R<UserQuestionResultVO> doJudgeJavaCode(@RequestBody JudgeSubmitDTO judgeSubmitDTO);

    @PostMapping("/judge/runJavaCode")
    R<UserCodeRunVO> runJavaCode(@RequestBody JudgeSubmitDTO judgeSubmitDTO);
}

