package com.sintao.common.mybatis.id;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "syncode.id.logical-clock")
public class LogicalSnowflakeProperties {

    private boolean enabled;
    private Long workerId;
    private String stateFile = "./data/id-generator/high-watermark.properties";
    private long reservationMillis = 10_000L;
    private long epochMillis = LogicalClockSnowflake.DEFAULT_EPOCH_MILLIS;

    public boolean isEnabled() {
        return enabled;
    }

    public void setEnabled(boolean enabled) {
        this.enabled = enabled;
    }

    public Long getWorkerId() {
        return workerId;
    }

    public void setWorkerId(Long workerId) {
        this.workerId = workerId;
    }

    public String getStateFile() {
        return stateFile;
    }

    public void setStateFile(String stateFile) {
        this.stateFile = stateFile;
    }

    public long getReservationMillis() {
        return reservationMillis;
    }

    public void setReservationMillis(long reservationMillis) {
        this.reservationMillis = reservationMillis;
    }

    public long getEpochMillis() {
        return epochMillis;
    }

    public void setEpochMillis(long epochMillis) {
        this.epochMillis = epochMillis;
    }
}
