package com.sintao.friend.controller.user;

import com.sintao.api.domain.vo.UserCodeRunVO;
import com.sintao.api.domain.vo.UserQuestionResultVO;
import com.sintao.common.core.controller.BaseController;
import com.sintao.common.core.domain.R;
import com.sintao.friend.domain.user.dto.UserRunDTO;
import com.sintao.friend.domain.user.dto.UserSubmitDTO;
import com.sintao.friend.domain.user.vo.AsyncSubmitResponseVO;
import com.sintao.friend.domain.user.vo.UserSubmissionHistoryVO;
import com.sintao.friend.service.user.IUserQuestionService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.enums.ParameterIn;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/user/question")
@Tag(name = "用户答题接口", description = "用户运行代码、提交代码、查询判题结果和查看提交记录")
public class UserQuestionController extends BaseController {

    @Autowired
    private IUserQuestionService userQuestionService;

    @PostMapping("/run")
    @Operation(summary = "运行代码", description = "仅在当前工作区运行代码，不写入正式提交记录")
    @ApiResponse(responseCode = "200", description = "运行完成并返回输出")
    @ApiResponse(responseCode = "2000", description = "不支持的语言类型或运行失败")
    public R<UserCodeRunVO> run(@RequestBody UserRunDTO runDTO) {
        return userQuestionService.run(runDTO);
    }

    @PostMapping("/submit")
    @Operation(summary = "同步提交代码", description = "提交代码并同步等待判题结果")
    @ApiResponse(responseCode = "200", description = "判题完成并返回结果")
    @ApiResponse(responseCode = "2000", description = "不支持的语言类型或判题失败")
    public R<UserQuestionResultVO> submit(@RequestBody UserSubmitDTO submitDTO) {
        return userQuestionService.submit(submitDTO);
    }

    @PostMapping("/rabbit/submit")
    @Operation(summary = "异步提交代码", description = "通过 RabbitMQ 异步提交代码，返回 requestId 供后续查询")
    @ApiResponse(responseCode = "200", description = "提交成功")
    @ApiResponse(responseCode = "2000", description = "不支持的语言类型或消息发送失败")
    public R<AsyncSubmitResponseVO> rabbitSubmit(@RequestBody UserSubmitDTO submitDTO) {
        return R.ok(userQuestionService.rabbitSubmit(submitDTO));
    }

    @GetMapping("/exe/result")
    @Operation(summary = "查询判题结果", description = "优先按 requestId 查询异步判题结果，未传 requestId 时回退到原有时间窗口查询")
    @Parameter(name = "examId", in = ParameterIn.QUERY, description = "测试ID，练习题可为空")
    @Parameter(name = "questionId", in = ParameterIn.QUERY, description = "题目ID", required = true)
    @Parameter(name = "currentTime", in = ParameterIn.QUERY, description = "提交时间，用于兼容原有时间窗口查询")
    @Parameter(name = "requestId", in = ParameterIn.QUERY, description = "异步请求ID")
    @ApiResponse(responseCode = "200", description = "成功返回判题结果")
    public R<UserQuestionResultVO> exeResult(
            @Parameter(description = "测试ID") Long examId,
            @Parameter(description = "题目ID") Long questionId,
            @Parameter(description = "提交时间") String currentTime,
            @Parameter(description = "异步请求ID") String requestId) {
        return R.ok(userQuestionService.exeResult(examId, questionId, currentTime, requestId));
    }

    @GetMapping("/submission/list")
    @Operation(summary = "提交记录", description = "查询当前登录用户在某道题下最近的提交记录列表")
    @Parameter(name = "examId", in = ParameterIn.QUERY, description = "测试ID，练习题可为空")
    @Parameter(name = "questionId", in = ParameterIn.QUERY, description = "题目ID", required = true)
    @ApiResponse(responseCode = "200", description = "成功返回提交记录列表")
    public R<List<UserSubmissionHistoryVO>> submissionHistory(
            @Parameter(description = "测试ID") Long examId,
            @Parameter(description = "题目ID") Long questionId) {
        return R.ok(userQuestionService.submissionHistory(examId, questionId));
    }
}
