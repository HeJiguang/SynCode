package com.sintao.friend.controller.exam;

import com.sintao.common.core.controller.BaseController;
import com.sintao.common.core.domain.R;
import com.sintao.common.core.domain.TableDataInfo;
import com.sintao.friend.domain.exam.dto.ExamQueryDTO;
import com.sintao.friend.domain.exam.dto.ExamRankDTO;
import com.sintao.friend.domain.exam.dto.ExamSubmissionDTO;
import com.sintao.friend.domain.exam.dto.HeartbeatDTO;
import com.sintao.friend.domain.exam.dto.SaveAnswerDTO;
import com.sintao.friend.domain.exam.dto.StartExamDTO;
import com.sintao.friend.domain.exam.vo.ExamAccessVO;
import com.sintao.friend.domain.exam.vo.ExamAnswerVO;
import com.sintao.friend.domain.exam.vo.ExamAttemptVO;
import com.sintao.friend.domain.exam.vo.ExamFinalizeVO;
import com.sintao.friend.domain.exam.vo.ExamSubmissionVO;
import com.sintao.friend.domain.exam.vo.HeartbeatVO;
import com.sintao.friend.service.exam.IExamService;
import com.sintao.friend.service.exam.ITrustedExamService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.enums.ParameterIn;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import jakarta.servlet.http.HttpServletRequest;

@RestController
@RequestMapping("/exam")
@Tag(name = "C 端测试接口", description = "阶段测试列表、排名和测试内题目切换等接口，部分接口支持半登录访问")
public class ExamController extends BaseController {

    @Autowired
    private IExamService examService;

    @Autowired
    private ITrustedExamService trustedExamService;

    @GetMapping("/semiLogin/list")
    @Operation(summary = "测试列表", description = "分页查询测试列表，从数据库读取")
    @ApiResponse(responseCode = "200", description = "成功返回分页数据")
    public TableDataInfo list(ExamQueryDTO examQueryDTO) {
        return getTableDataInfo(examService.list(examQueryDTO));
    }

    @GetMapping("/semiLogin/redis/list")
    @Operation(summary = "测试列表(Redis)", description = "分页查询测试列表，优先从 Redis 缓存获取，支持进行中或历史测试")
    @ApiResponse(responseCode = "200", description = "成功返回分页数据")
    public TableDataInfo redisList(ExamQueryDTO examQueryDTO) {
        return examService.redisList(examQueryDTO);
    }

    @GetMapping("/rank/list")
    @Operation(summary = "测试排名", description = "分页查询指定测试的排行榜")
    @ApiResponse(responseCode = "200", description = "成功返回分页数据")
    public TableDataInfo rankList(ExamRankDTO examRankDTO) {
        return examService.rankList(examRankDTO);
    }

    @GetMapping("/getFirstQuestion")
    @Operation(summary = "获取测试第一题", description = "获取测试中题目的第一题ID")
    @Parameter(name = "examId", in = ParameterIn.QUERY, description = "测试ID", required = true)
    @ApiResponse(responseCode = "200", description = "成功返回第一题ID")
    @ApiResponse(responseCode = "2000", description = "测试不存在或没有题目")
    public R<String> getFirstQuestion(@Parameter(description = "测试ID") Long examId) {
        return R.ok(examService.getFirstQuestion(examId));
    }

    @GetMapping("/preQuestion")
    @Operation(summary = "测试内上一题", description = "获取测试中当前题目的上一题ID")
    @Parameter(name = "examId", in = ParameterIn.QUERY, description = "测试ID", required = true)
    @Parameter(name = "questionId", in = ParameterIn.QUERY, description = "当前题目ID", required = true)
    @ApiResponse(responseCode = "200", description = "成功返回上一题ID")
    @ApiResponse(responseCode = "2000", description = "已经是第一题")
    public R<String> preQuestion(
            @Parameter(description = "测试ID") Long examId,
            @Parameter(description = "当前题目ID") Long questionId) {
        return R.ok(examService.preQuestion(examId, questionId));
    }

    @GetMapping("/nextQuestion")
    @Operation(summary = "测试内下一题", description = "获取测试中当前题目的下一题ID")
    @Parameter(name = "examId", in = ParameterIn.QUERY, description = "测试ID", required = true)
    @Parameter(name = "questionId", in = ParameterIn.QUERY, description = "当前题目ID", required = true)
    @ApiResponse(responseCode = "200", description = "成功返回下一题ID")
    @ApiResponse(responseCode = "2000", description = "已经是最后一题")
    public R<String> nextQuestion(
            @Parameter(description = "测试ID") Long examId,
            @Parameter(description = "当前题目ID") Long questionId) {
        return R.ok(examService.nextQuestion(examId, questionId));
    }

    @GetMapping("/{examId}/access")
    @Operation(summary = "考试进入检查", description = "检查资格、服务器时间、入场窗口和可恢复作答")
    public R<ExamAccessVO> access(@PathVariable Long examId) {
        return R.ok(trustedExamService.access(examId));
    }

    @PostMapping("/{examId}/attempts/start")
    @Operation(summary = "开始或恢复考试", description = "以服务器时间创建唯一作答并返回不可变题目快照")
    public R<ExamAttemptVO> start(
            @PathVariable Long examId,
            @RequestBody StartExamDTO body,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @RequestHeader(value = "X-Request-ID", required = false) String requestId,
            HttpServletRequest request) {
        return R.ok(trustedExamService.start(examId, body, idempotencyKey, requestId,
                clientIp(request), request.getHeader("User-Agent")));
    }

    @GetMapping("/{examId}/attempts/current")
    @Operation(summary = "恢复当前考试", description = "刷新或重连后恢复同一作答、截止时间和最新答案")
    public R<ExamAttemptVO> current(@PathVariable Long examId) {
        return R.ok(trustedExamService.current(examId));
    }

    @PostMapping("/attempts/{attemptId}/heartbeat")
    @Operation(summary = "考试心跳", description = "同步服务端时间、截止时间和活动会话")
    public R<HeartbeatVO> heartbeat(@PathVariable Long attemptId,
                                    @RequestBody HeartbeatDTO body,
                                    HttpServletRequest request) {
        return R.ok(trustedExamService.heartbeat(attemptId, body, clientIp(request)));
    }

    @PutMapping("/attempts/{attemptId}/answers/{versionQuestionId}")
    @Operation(summary = "自动保存答案", description = "通过 expectedVersion 防止旧请求覆盖新答案")
    public R<ExamAnswerVO> saveAnswer(@PathVariable Long attemptId,
                                      @PathVariable Long versionQuestionId,
                                      @RequestBody SaveAnswerDTO body) {
        return R.ok(trustedExamService.saveAnswer(attemptId, versionQuestionId, body));
    }

    @PostMapping("/attempts/{attemptId}/submissions")
    @Operation(summary = "提交单题判题", description = "提交不可变答案版本到异步判题链")
    public R<ExamSubmissionVO> submit(@PathVariable Long attemptId,
                                      @RequestBody ExamSubmissionDTO body,
                                      @RequestHeader("Idempotency-Key") String requestId) {
        return R.ok(trustedExamService.submit(attemptId, body, requestId));
    }

    @PostMapping("/attempts/{attemptId}/finalize")
    @Operation(summary = "交卷", description = "幂等冻结全部已保存答案并进入成绩处理")
    public R<ExamFinalizeVO> finalizeAttempt(
            @PathVariable Long attemptId,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @RequestHeader(value = "X-Request-ID", required = false) String requestId) {
        return R.ok(trustedExamService.finalizeAttempt(attemptId, idempotencyKey, requestId));
    }

    @GetMapping("/attempts/{attemptId}/receipt")
    @Operation(summary = "交卷回执", description = "查询服务端确认的终态和成绩处理状态")
    public R<ExamFinalizeVO> receipt(@PathVariable Long attemptId) {
        return R.ok(trustedExamService.receipt(attemptId));
    }

    private String clientIp(HttpServletRequest request) {
        String forwarded = request.getHeader("X-Forwarded-For");
        if (forwarded == null || forwarded.isBlank()) {
            return request.getRemoteAddr();
        }
        int comma = forwarded.indexOf(',');
        return (comma < 0 ? forwarded : forwarded.substring(0, comma)).trim();
    }
}
