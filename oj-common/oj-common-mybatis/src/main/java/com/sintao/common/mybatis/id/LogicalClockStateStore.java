package com.sintao.common.mybatis.id;

import java.util.OptionalLong;

public interface LogicalClockStateStore extends AutoCloseable {

    OptionalLong loadHighWatermark(long workerId);

    void persistHighWatermark(long workerId, long highWatermark);

    @Override
    default void close() {
    }
}
