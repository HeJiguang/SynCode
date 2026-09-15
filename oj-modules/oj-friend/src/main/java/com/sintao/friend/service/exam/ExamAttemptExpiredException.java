package com.sintao.friend.service.exam;

import com.sintao.common.core.enums.ResultCode;
import com.sintao.common.security.exception.ServiceException;

public class ExamAttemptExpiredException extends ServiceException {
    public ExamAttemptExpiredException() {
        super(ResultCode.EXAM_ATTEMPT_EXPIRED);
    }
}
