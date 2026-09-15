package com.sintao.system.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.Clock;

@Configuration
public class TrustedExamTimeConfig {

    @Bean
    public Clock trustedExamClock() {
        return Clock.systemUTC();
    }
}
