package com.sintao.common.core.domain;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.sintao.common.core.enums.ResultCode;

@JsonInclude(JsonInclude.Include.NON_NULL)
public class R<T> {

    private int code;
    private String msg;
    private T data;
    private Object details;

    public static <T> R<T> ok() {
        return assembleResult(null, ResultCode.SUCCESS);
    }

    public static <T> R<T> ok(T data) {
        return assembleResult(data, ResultCode.SUCCESS);
    }

    public static <T> R<T> fail() {
        return assembleResult(null, ResultCode.FAILED);
    }

    public static <T> R<T> fail(int code, String msg) {
        return assembleResult(code, msg, null);
    }

    public static <T> R<T> fail(ResultCode resultCode) {
        return assembleResult(null, resultCode);
    }

    public static <T> R<T> fail(ResultCode resultCode, Object details) {
        R<T> result = assembleResult(null, resultCode);
        result.setDetails(details);
        return result;
    }

    private static <T> R<T> assembleResult(T data, ResultCode resultCode) {
        R<T> r = new R<>();
        r.setCode(resultCode.getCode());
        r.setData(data);
        r.setMsg(resultCode.getMsg());
        return r;
    }

    private static <T> R<T> assembleResult(int code, String msg, T data) {
        R<T> r = new R<>();
        r.setCode(code);
        r.setData(data);
        r.setMsg(msg);
        return r;
    }

    public int getCode() {
        return code;
    }

    public void setCode(int code) {
        this.code = code;
    }

    public String getMsg() {
        return msg;
    }

    public void setMsg(String msg) {
        this.msg = msg;
    }

    public T getData() {
        return data;
    }

    public void setData(T data) {
        this.data = data;
    }

    public Object getDetails() {
        return details;
    }

    public void setDetails(Object details) {
        this.details = details;
    }
}
