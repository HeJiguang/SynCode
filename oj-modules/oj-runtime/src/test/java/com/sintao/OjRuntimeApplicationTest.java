package com.sintao;

import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.ComponentScan;

import static org.assertj.core.api.Assertions.assertThat;

class OjRuntimeApplicationTest {

    @Test
    void componentScanKeepsCommonModulesOnAutoConfigurationBoundary() {
        ComponentScan componentScan = OjRuntimeApplication.class.getAnnotation(ComponentScan.class);

        assertThat(componentScan.basePackages())
                .containsExactlyInAnyOrder(
                        "com.sintao.runtime",
                        "com.sintao.system",
                        "com.sintao.friend",
                        "com.sintao.job"
                )
                .doesNotContain("com.sintao", "com.sintao.common");
    }
}
