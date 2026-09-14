package com.sintao.friend.service.exam;

import com.sintao.friend.domain.exam.dto.ExamSubmissionDTO;
import com.sintao.friend.domain.exam.dto.HeartbeatDTO;
import com.sintao.friend.domain.exam.dto.SaveAnswerDTO;
import com.sintao.friend.domain.exam.dto.StartExamDTO;
import com.sintao.friend.domain.exam.vo.ExamAccessVO;
import com.sintao.friend.domain.exam.vo.ExamAnswerVO;
import com.sintao.friend.domain.exam.vo.ExamAttemptVO;
import com.sintao.friend.domain.exam.vo.ExamFinalizeVO;
import com.sintao.friend.domain.exam.vo.ExamSubmissionVO;
import com.sintao.friend.domain.exam.vo.HeartbeatVO;

public interface ITrustedExamService {
    ExamAccessVO access(Long examId);
    ExamAttemptVO start(Long examId, StartExamDTO request, String idempotencyKey,
                        String requestId, String ipAddress, String userAgent);
    ExamAttemptVO current(Long examId);
    HeartbeatVO heartbeat(Long attemptId, HeartbeatDTO request, String ipAddress);
    ExamAnswerVO saveAnswer(Long attemptId, Long versionQuestionId, SaveAnswerDTO request);
    ExamSubmissionVO submit(Long attemptId, ExamSubmissionDTO request, String requestId);
    ExamFinalizeVO finalizeAttempt(Long attemptId, String idempotencyKey, String requestId);
    ExamFinalizeVO receipt(Long attemptId);
}
