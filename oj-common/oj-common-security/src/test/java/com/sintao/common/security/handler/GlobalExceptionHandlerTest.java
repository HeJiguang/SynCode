package com.sintao.common.security.handler;

import com.sintao.common.core.domain.R;
import com.sintao.common.core.enums.ResultCode;
import jakarta.servlet.http.HttpServletRequest;
import org.junit.jupiter.api.Test;
import org.springframework.core.MethodParameter;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;

import java.lang.reflect.Method;

import static org.junit.jupiter.api.Assertions.assertEquals;

class GlobalExceptionHandlerTest {

    private final GlobalExceptionHandler handler = new GlobalExceptionHandler();

    @Test
    void handleMethodArgumentTypeMismatchExceptionShouldReturnParamValidationError() throws NoSuchMethodException {
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/question/semiLogin/detail");
        Method method = QuestionEndpoint.class.getDeclaredMethod("detail", Long.class);
        MethodParameter parameter = new MethodParameter(method, 0);
        MethodArgumentTypeMismatchException exception = new MethodArgumentTypeMismatchException(
                "merge-intervals",
                Long.class,
                "questionId",
                parameter,
                new NumberFormatException("For input string: \"merge-intervals\"")
        );

        R<Void> response = handler.handleMethodArgumentTypeMismatchException(exception, request);

        assertEquals(ResultCode.FAILED_PARAMS_VALIDATE.getCode(), response.getCode());
        assertEquals("参数 'questionId' 的值 'merge-intervals' 无效", response.getMsg());
    }

    private static final class QuestionEndpoint {
        @SuppressWarnings("unused")
        private void detail(Long questionId) {
        }
    }
}
