package com.sintao.job.handler;

import com.sintao.job.service.TrustedExamReconciliationService;
import com.xxl.job.core.handler.annotation.XxlJob;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
@Slf4j
public class TrustedExamXxlJob {

    private final TrustedExamReconciliationService reconciliationService;

    @XxlJob("trustedExamReconciliationHandler")
    public void reconcile() {
        int expired = reconciliationService.finalizeExpiredAttempts();
        int graded = reconciliationService.aggregateTerminalGrades();
        int finished = reconciliationService.finishEndedExams();
        int released = reconciliationService.releaseScheduledResults();
        int purgedEvidence = reconciliationService.purgeExpiredIntegrityEvidence();
        log.info("Trusted exam reconciliation finished: expired={}, graded={}, finished={}, released={}, purgedEvidence={}",
                expired, graded, finished, released, purgedEvidence);
    }
}
