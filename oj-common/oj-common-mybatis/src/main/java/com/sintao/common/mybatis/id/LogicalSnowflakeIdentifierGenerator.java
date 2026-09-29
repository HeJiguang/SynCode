package com.sintao.common.mybatis.id;

import com.baomidou.mybatisplus.core.incrementer.IdentifierGenerator;

public final class LogicalSnowflakeIdentifierGenerator implements IdentifierGenerator, AutoCloseable {

    private final LogicalClockSnowflake snowflake;

    public LogicalSnowflakeIdentifierGenerator(LogicalClockSnowflake snowflake) {
        this.snowflake = snowflake;
    }

    @Override
    public Long nextId(Object entity) {
        return snowflake.nextId();
    }

    @Override
    public void close() {
        snowflake.close();
    }
}
