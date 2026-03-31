package com.sintao.friend.service.user;

import com.sintao.api.domain.vo.UserCodeRunVO;
import com.sintao.api.domain.vo.UserQuestionResultVO;
import com.sintao.common.core.domain.R;
import com.sintao.friend.domain.user.dto.UserRunDTO;
import com.sintao.friend.domain.user.dto.UserSubmitDTO;
import com.sintao.friend.domain.user.vo.AsyncSubmitResponseVO;
import com.sintao.friend.domain.user.vo.UserSubmissionHistoryVO;

import java.util.List;

public interface IUserQuestionService {

    R<UserCodeRunVO> run(UserRunDTO runDTO);

    R<UserQuestionResultVO> submit(UserSubmitDTO submitDTO);

    AsyncSubmitResponseVO rabbitSubmit(UserSubmitDTO submitDTO);

    UserQuestionResultVO exeResult(Long examId, Long questionId, String currentTime, String requestId);

    List<UserSubmissionHistoryVO> submissionHistory(Long examId, Long questionId);
}
