package com.sintao.system.domain.exam.vo;

import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;
import java.util.List;

@Getter
@Setter
public class ExamMonitorVO {
    private Long examId;
    private String status;
    private LocalDateTime serverNow;
    private int authorized;
    private int notStarted;
    private int inProgress;
    private int disconnected;
    private int submitted;
    private int timedOut;
    private int cancelled;
    private List<ExamCandidateVO> candidates;
}
