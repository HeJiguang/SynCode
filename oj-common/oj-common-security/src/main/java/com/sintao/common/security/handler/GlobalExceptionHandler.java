package com.sintao.common.security.handler;

import cn.hutool.core.collection.CollUtil;
import cn.hutool.core.util.StrUtil;
import com.sintao.common.core.domain.R;
import com.sintao.common.core.enums.ResultCode;
import com.sintao.common.security.exception.ServiceException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.support.DefaultMessageSourceResolvable;
import org.springframework.validation.BindException;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;

import java.util.Collection;
import java.util.Objects;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * 全局异常处理器
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    /**
     * 请求方式不支持
     */
    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    public R<?> handleHttpRequestMethodNotSupported(HttpRequestMethodNotSupportedException e,
                                                    HttpServletRequest request) {
        String requestURI = request.getRequestURI();
        log.error("请求地址 '{}'，不支持 '{}' 请求", requestURI, e.getMethod());
        return R.fail(ResultCode.ERROR);
    }

    @ExceptionHandler(ServiceException.class)
    public R<?> handleServiceException(ServiceException e, HttpServletRequest request,
                                       HttpServletResponse response) {
        String requestURI = request.getRequestURI();
        ResultCode resultCode = e.getResultCode();
        log.error("请求地址 '{}'，发生业务异常：{}", requestURI, resultCode.getMsg(), e);
        response.setStatus(httpStatus(resultCode));
        return R.fail(resultCode, e.getDetails());
    }

    private int httpStatus(ResultCode resultCode) {
        return switch (resultCode) {
            case EXAM_CANDIDATE_NOT_AUTHORIZED, EXAM_RESULT_NOT_RELEASED -> 403;
            case EXAM_ATTEMPT_NOT_FOUND, EXAM_ANSWER_NOT_FOUND, EXAM_QUESTION_NOT_IN_VERSION,
                    FAILED_NOT_EXISTS, EXAM_NOT_EXISTS -> 404;
            case EXAM_CANCELLED, EXAM_ADMISSION_CLOSED, EXAM_ATTEMPT_EXPIRED -> 410;
            case EXAM_PUBLISH_VALIDATION_FAILED, EXAM_INTEGRITY_EVENT_REJECTED -> 422;
            case EXAM_SUBMISSION_LIMIT_REACHED -> 429;
            case EXAM_FINALIZATION_PENDING -> 202;
            case EXAM_STATE_CONFLICT, EXAM_NOT_PUBLISHED, EXAM_ACCESS_TOO_EARLY,
                    EXAM_ATTEMPT_TERMINAL, EXAM_ANSWER_VERSION_CONFLICT,
                    EXAM_IDEMPOTENCY_CONFLICT, EXAM_GRADE_NOT_READY,
                    EXAM_COMMAND_IN_PROGRESS, EXAM_SESSION_CONFLICT -> 409;
            default -> 400;
        };
    }

    @ExceptionHandler(BindException.class)
    public R<Void> handleBindException(BindException e) {
        log.error(e.getMessage());
        String message = join(e.getAllErrors(), DefaultMessageSourceResolvable::getDefaultMessage, ", ");
        return R.fail(ResultCode.FAILED_PARAMS_VALIDATE.getCode(), message);
    }

    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    public R<Void> handleMethodArgumentTypeMismatchException(MethodArgumentTypeMismatchException e,
                                                             HttpServletRequest request) {
        String requestURI = request.getRequestURI();
        String parameterName = e.getName();
        Object invalidValue = e.getValue();
        String message = String.format("参数 '%s' 的值 '%s' 无效", parameterName, invalidValue);
        log.warn("请求地址 '{}'，参数类型转换失败，parameter={}, value={}", requestURI, parameterName, invalidValue);
        return R.fail(ResultCode.FAILED_PARAMS_VALIDATE.getCode(), message);
    }

    private <E> String join(Collection<E> collection, Function<E, String> function, CharSequence delimiter) {
        if (CollUtil.isEmpty(collection)) {
            return StrUtil.EMPTY;
        }
        return collection.stream()
                .map(function)
                .filter(Objects::nonNull)
                .collect(Collectors.joining(delimiter));
    }

    /**
     * 拦截运行时异常
     */
    @ExceptionHandler(RuntimeException.class)
    public R<?> handleRuntimeException(RuntimeException e, HttpServletRequest request) {
        String requestURI = request.getRequestURI();
        log.error("请求地址 '{}'，发生运行时异常。", requestURI, e);
        return R.fail(ResultCode.ERROR);
    }

    /**
     * 系统异常
     */
    @ExceptionHandler(Exception.class)
    public R<?> handleException(Exception e, HttpServletRequest request) {
        String requestURI = request.getRequestURI();
        log.error("请求地址 '{}'，发生异常。", requestURI, e);
        return R.fail(ResultCode.ERROR);
    }
}
