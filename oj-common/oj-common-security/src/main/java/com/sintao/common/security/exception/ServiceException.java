package com.sintao.common.security.exception;

import com.sintao.common.core.enums.ResultCode;

public class ServiceException extends RuntimeException {

    private final ResultCode resultCode;
    private final Object details;

    public ServiceException(ResultCode resultCode) {
        this(resultCode, null);
    }

    public ServiceException(ResultCode resultCode, Object details) {
        super(resultCode.getMsg());
        this.resultCode = resultCode;
        this.details = details;
    }

    public ResultCode getResultCode() {
        return resultCode;
    }

    public Object getDetails() {
        return details;
    }
}
