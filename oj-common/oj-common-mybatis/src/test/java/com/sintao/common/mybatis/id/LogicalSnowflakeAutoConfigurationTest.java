package com.sintao.common.mybatis.id;

import com.baomidou.mybatisplus.core.incrementer.IdentifierGenerator;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.boot.autoconfigure.AutoConfigurations;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;

import java.nio.file.Path;

import static org.assertj.core.api.Assertions.assertThat;

class LogicalSnowflakeAutoConfigurationTest {

    @TempDir
    Path temporaryDirectory;

    private final ApplicationContextRunner contextRunner = new ApplicationContextRunner()
            .withConfiguration(AutoConfigurations.of(LogicalSnowflakeAutoConfiguration.class));

    @Test
    void remainsDisabledUnlessExplicitlyEnabled() {
        contextRunner.run(context -> assertThat(context).doesNotHaveBean(IdentifierGenerator.class));
    }

    @Test
    void registersMybatisIdentifierGenerator() {
        String stateFile = temporaryDirectory.resolve("auto-config.properties").toString();
        contextRunner
                .withPropertyValues(
                        "syncode.id.logical-clock.enabled=true",
                        "syncode.id.logical-clock.worker-id=21",
                        "syncode.id.logical-clock.state-file=" + stateFile)
                .run(context -> {
                    assertThat(context).hasSingleBean(IdentifierGenerator.class);
                    IdentifierGenerator generator = context.getBean(IdentifierGenerator.class);
                    assertThat(generator.nextId(new Object())).isInstanceOf(Long.class);
                });
    }

    @Test
    void failsFastWithoutWorkerId() {
        contextRunner
                .withPropertyValues(
                        "syncode.id.logical-clock.enabled=true",
                        "syncode.id.logical-clock.state-file="
                                + temporaryDirectory.resolve("missing-worker.properties"))
                .run(context -> assertThat(context).hasFailed());
    }
}
