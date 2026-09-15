package com.sintao.runtime.config;

import com.sintao.job.service.TrustedExamReconciliationService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.scheduling.concurrent.ThreadPoolTaskScheduler;
import org.springframework.web.method.HandlerTypePredicate;
import org.springframework.web.servlet.config.annotation.PathMatchConfigurer;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;
import org.springframework.web.util.pattern.PathPatternParser;

import java.time.Clock;

@Configuration
public class CompactRuntimeConfiguration implements WebMvcConfigurer {

    @Bean
    public Clock trustedExamClock() {
        return Clock.systemUTC();
    }

    @Bean
    public ThreadPoolTaskScheduler taskScheduler() {
        ThreadPoolTaskScheduler scheduler = new ThreadPoolTaskScheduler();
        scheduler.setPoolSize(2);
        scheduler.setThreadNamePrefix("oj-runtime-job-");
        return scheduler;
    }

    @Override
    public void configurePathMatch(PathMatchConfigurer configurer) {
        configurer.setPatternParser(new PathPatternParser());
        configurer.addPathPrefix(
                "/system",
                HandlerTypePredicate.forBasePackage("com.sintao.system.controller")
        );
        configurer.addPathPrefix(
                "/friend",
                HandlerTypePredicate.forBasePackage("com.sintao.friend.controller")
        );
    }

    @Configuration
    @RequiredArgsConstructor
    @Slf4j
    static class TrustedExamScheduler {

        private final TrustedExamReconciliationService reconciliationService;

        @Scheduled(fixedDelayString = "${syncode.runtime.reconciliation-delay-ms:15000}")
        public void reconcile() {
            int expired = reconciliationService.finalizeExpiredAttempts();
            int graded = reconciliationService.aggregateTerminalGrades();
            int finished = reconciliationService.finishEndedExams();
            int released = reconciliationService.releaseScheduledResults();
            int purgedEvidence = reconciliationService.purgeExpiredIntegrityEvidence();
            log.info("Compact reconciliation finished: expired={}, graded={}, finished={}, released={}, purgedEvidence={}",
                    expired, graded, finished, released, purgedEvidence);
        }
    }
}
