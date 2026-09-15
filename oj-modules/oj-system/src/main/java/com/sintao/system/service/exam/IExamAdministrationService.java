package com.sintao.system.service.exam;

import com.sintao.system.domain.exam.dto.CandidateAuthorizationDTO;
import com.sintao.system.domain.exam.vo.ExamCandidateVO;
import com.sintao.system.domain.exam.vo.ExamGradeVO;
import com.sintao.system.domain.exam.vo.ExamEvidenceEventVO;
import com.sintao.system.domain.exam.vo.ExamMonitorVO;

import java.util.List;

public interface IExamAdministrationService {
    List<ExamCandidateVO> authorizeCandidates(Long examId, CandidateAuthorizationDTO request, String requestId);
    void revokeCandidate(Long examId, Long userId, String reason, String requestId);
    List<ExamCandidateVO> candidates(Long examId);
    void cancel(Long examId, String reason, String requestId);
    ExamMonitorVO monitor(Long examId);
    List<ExamGradeVO> grades(Long examId);
    void releaseResults(Long examId, String idempotencyKey, String requestId);
    List<ExamEvidenceEventVO> evidence(Long examId, Long attemptId);
}
