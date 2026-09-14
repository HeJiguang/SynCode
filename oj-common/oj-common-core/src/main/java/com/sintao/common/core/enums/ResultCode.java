package com.sintao.common.core.enums;

public enum ResultCode {

    SUCCESS(1000, "操作成功"),
    ERROR(2000, "服务繁忙，请稍后重试"),

    FAILED(3000, "操作失败"),
    FAILED_UNAUTHORIZED(3001, "未授权"),
    FAILED_PARAMS_VALIDATE(3002, "参数校验失败"),
    FAILED_NOT_EXISTS(3003, "资源不存在"),
    FAILED_ALREADY_EXISTS(3004, "资源已存在"),

    FAILED_USER_EXISTS(3101, "用户已存在"),
    FAILED_USER_NOT_EXISTS(3102, "用户不存在"),
    FAILED_LOGIN(3103, "账号或密码错误"),
    FAILED_USER_BANNED(3104, "您已被列入黑名单，请联系管理员"),
    FAILED_USER_PHONE(3105, "你输入的手机号有误"),
    FAILED_FREQUENT(3106, "操作频繁，请稍后重试"),
    FAILED_TIME_LIMIT(3107, "当天请求次数已达到上限"),
    FAILED_SEND_CODE(3108, "验证码发送错误"),
    FAILED_INVALID_CODE(3109, "验证码无效"),
    FAILED_ERROR_CODE(3110, "验证码错误"),
    FAILED_USER_EMAIL(3111, "你输入的邮箱有误"),

    EXAM_START_TIME_BEFORE_CURRENT_TIME(3201, "竞赛开始时间不能早于当前时间"),
    EXAM_START_TIME_AFTER_END_TIME(3202, "竞赛开始时间不能晚于竞赛结束时间"),
    EXAM_NOT_EXISTS(3203, "竞赛不存在"),
    EXAM_QUESTION_NOT_EXISTS(3204, "新增到竞赛中的题目不存在"),
    EXAM_STARTED(3205, "竞赛已经开始，无法进行当前操作"),
    EXAM_NOT_HAS_QUESTION(3206, "竞赛中不包含题目"),
    EXAM_IS_FINISH(3207, "竞赛已经结束，不能进行当前操作"),
    EXAM_IS_PUBLISH(3208, "竞赛已经发布，不能进行编辑或删除操作"),
    EXAM_NOT_STARTED(3209, "考试尚未开始"),
    USER_EXAM_NOT_ENTERED(3210, "未报名，无法进入考试"),

    EXAM_STATE_CONFLICT(3220, "考试状态不允许当前操作"),
    EXAM_NOT_PUBLISHED(3221, "考试尚未发布"),
    EXAM_CANCELLED(3222, "考试已取消"),
    EXAM_ACCESS_TOO_EARLY(3223, "考试尚未开放进入"),
    EXAM_ADMISSION_CLOSED(3224, "考试入场时间已截止"),
    EXAM_CANDIDATE_NOT_AUTHORIZED(3225, "没有本场考试资格"),
    EXAM_ATTEMPT_NOT_FOUND(3226, "未找到考试作答记录"),
    EXAM_ATTEMPT_TERMINAL(3227, "考试已经交卷，不能继续作答"),
    EXAM_ATTEMPT_EXPIRED(3228, "考试作答时间已截止"),
    EXAM_ANSWER_VERSION_CONFLICT(3229, "答案版本冲突，请先恢复最新答案"),
    EXAM_IDEMPOTENCY_CONFLICT(3230, "幂等键已用于不同请求"),
    EXAM_SUBMISSION_LIMIT_REACHED(3231, "本题正式提交次数已达上限"),
    EXAM_RESULT_NOT_RELEASED(3232, "成绩尚未发布"),
    EXAM_GRADE_NOT_READY(3233, "成绩仍在计算中"),
    EXAM_PUBLISH_VALIDATION_FAILED(3234, "试卷未通过发布校验"),
    EXAM_COMMAND_IN_PROGRESS(3235, "相同命令正在处理中"),
    EXAM_SESSION_CONFLICT(3236, "检测到其他活动考试会话"),
    EXAM_ANSWER_NOT_FOUND(3237, "未找到题目答案"),
    EXAM_QUESTION_NOT_IN_VERSION(3238, "题目不属于当前试卷版本"),
    EXAM_INTEGRITY_EVENT_REJECTED(3239, "诚信事件数据无效"),
    EXAM_FINALIZATION_PENDING(3240, "交卷正在处理中"),

    USER_EXAM_HAS_ENTER(3301, "用户已经报名，无需重复报名"),

    FAILED_FILE_UPLOAD(3401, "文件上传失败"),
    FAILED_FILE_UPLOAD_TIME_LIMIT(3402, "当天上传图片数量超过上限"),

    FAILED_FIRST_QUESTION(3501, "当前题目已经是第一题了"),
    FAILED_LAST_QUESTION(3502, "当前题目已经是最后一题了"),
    FAILED_NOT_SUPPORT_PROGRAM(3601, "当前不支持此语言"),
    FAILED_RABBIT_PRODUCE(3701, "MQ 生产消息异常");

    private final int code;
    private final String msg;

    ResultCode(int code, String msg) {
        this.code = code;
        this.msg = msg;
    }

    public int getCode() {
        return code;
    }

    public String getMsg() {
        return msg;
    }
}
