package com.sintao.common.mybatis.id;

import com.baomidou.mybatisplus.autoconfigure.MybatisPlusAutoConfiguration;
import com.baomidou.mybatisplus.core.incrementer.IdentifierGenerator;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.AutoConfigureBefore;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;

import java.nio.file.Path;
import java.time.Clock;

@AutoConfiguration
@AutoConfigureBefore(MybatisPlusAutoConfiguration.class)
@EnableConfigurationProperties(LogicalSnowflakeProperties.class)
@ConditionalOnProperty(prefix = "syncode.id.logical-clock", name = "enabled", havingValue = "true")
public class LogicalSnowflakeAutoConfiguration {

    @Bean(destroyMethod = "close")
    @ConditionalOnMissingBean(IdentifierGenerator.class)
    public IdentifierGenerator logicalSnowflakeIdentifierGenerator(LogicalSnowflakeProperties properties) {
        Long workerId = properties.getWorkerId();
        if (workerId == null) {
            throw new IllegalStateException(
                    "syncode.id.logical-clock.worker-id is required when logical-clock IDs are enabled");
        }
        if (properties.getStateFile() == null || properties.getStateFile().isBlank()) {
            throw new IllegalStateException(
                    "syncode.id.logical-clock.state-file is required when logical-clock IDs are enabled");
        }

        FileLogicalClockStateStore stateStore = new FileLogicalClockStateStore(Path.of(properties.getStateFile()));
        try {
            LogicalClockSnowflake snowflake = new LogicalClockSnowflake(
                    workerId,
                    properties.getEpochMillis(),
                    properties.getReservationMillis(),
                    Clock.systemUTC()::millis,
                    stateStore);
            return new LogicalSnowflakeIdentifierGenerator(snowflake);
        } catch (RuntimeException e) {
            stateStore.close();
            throw e;
        }
    }
}
