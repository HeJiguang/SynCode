package com.sintao.system.controller.exam;

import com.sintao.common.core.controller.BaseController;
import com.sintao.common.core.domain.R;
import com.sintao.common.core.domain.TableDataInfo;
import com.sintao.system.domain.exam.dto.ExamAddDTO;
import com.sintao.system.domain.exam.dto.ExamEditDTO;
import com.sintao.system.domain.exam.dto.ExamQueryDTO;
import com.sintao.system.domain.exam.dto.ExamQuestAddDTO;
import com.sintao.system.domain.exam.dto.ExamQuestionsReplaceDTO;
import com.sintao.system.domain.exam.vo.ExamDetailVO;
import com.sintao.system.domain.exam.vo.ExamPublicationVO;
import com.sintao.system.service.exam.IExamService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.enums.ParameterIn;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/exam")
@Tag(name = "后台测试管理接口")
public class ExamController extends BaseController {

    @Autowired
    private IExamService examService;

    @GetMapping("/list")
    @Operation(summary = "测试列表", description = "分页查询测试列表，支持按标题等条件筛选")
    @ApiResponse(responseCode = "200", description = "成功返回分页数据")
    public TableDataInfo list(ExamQueryDTO examQueryDTO) {
        return getTableDataInfo(examService.list(examQueryDTO));
    }

    @PostMapping("/add")
    @Operation(summary = "新增测试", description = "创建新的阶段测试，并返回测试ID")
    @ApiResponse(responseCode = "1000", description = "新增成功，返回测试ID")
    @ApiResponse(responseCode = "2000", description = "服务繁忙，请稍后重试")
    public R<String> add(@RequestBody ExamAddDTO examAddDTO) {
        return R.ok(examService.add(examAddDTO));
    }

    @PostMapping
    @Operation(summary = "创建考试草稿", description = "按可信考试契约创建可编辑草稿")
    public R<String> createDraft(@RequestBody ExamAddDTO request) {
        return R.ok(examService.add(request));
    }

    @PostMapping("/question/add")
    @Operation(summary = "测试添加题目", description = "为指定测试关联题目")
    @ApiResponse(responseCode = "1000", description = "添加成功")
    @ApiResponse(responseCode = "2000", description = "题目不存在、测试已发布或服务异常")
    public R<Void> questionAdd(@RequestBody ExamQuestAddDTO examQuestAddDTO) {
        return toR(examService.questionAdd(examQuestAddDTO));
    }

    @PutMapping("/{examId}/questions")
    @Operation(summary = "替换试卷题目", description = "原子替换草稿中的有序题目、分值和必答规则")
    public R<Void> replaceQuestions(@PathVariable Long examId,
                                    @RequestBody ExamQuestionsReplaceDTO request) {
        return toR(examService.replaceQuestions(examId, request));
    }

    @DeleteMapping("/question/delete")
    @Operation(summary = "测试移除题目", description = "从指定测试中移除题目")
    @Parameter(name = "examId", in = ParameterIn.QUERY, description = "测试ID", required = true)
    @Parameter(name = "questionId", in = ParameterIn.QUERY, description = "题目ID", required = true)
    @ApiResponse(responseCode = "1000", description = "移除成功")
    @ApiResponse(responseCode = "2000", description = "测试已发布或服务异常")
    public R<Void> questionDelete(
            @Parameter(description = "测试ID") Long examId,
            @Parameter(description = "题目ID") Long questionId) {
        return toR(examService.questionDelete(examId, questionId));
    }

    @GetMapping("/detail")
    @Operation(summary = "测试详情", description = "根据测试ID获取测试详情和关联题目")
    @Parameter(name = "examId", in = ParameterIn.QUERY, description = "测试ID", required = true)
    @ApiResponse(responseCode = "1000", description = "成功返回测试详情")
    @ApiResponse(responseCode = "2000", description = "测试不存在或服务异常")
    public R<ExamDetailVO> detail(@Parameter(description = "测试ID") Long examId) {
        return R.ok(examService.detail(examId));
    }

    @GetMapping("/{examId}")
    @Operation(summary = "读取考试", description = "读取草稿规则、组卷、当前版本和服务端允许操作")
    public R<ExamDetailVO> detailByPath(@PathVariable Long examId) {
        return R.ok(examService.detail(examId));
    }

    @PutMapping("/edit")
    @Operation(summary = "编辑测试", description = "更新测试信息，未发布测试可编辑")
    @ApiResponse(responseCode = "1000", description = "编辑成功")
    @ApiResponse(responseCode = "2000", description = "测试已发布或服务异常")
    public R<Void> edit(@RequestBody ExamEditDTO examEditDTO) {
        return toR(examService.edit(examEditDTO));
    }

    @PutMapping("/{examId}")
    @Operation(summary = "编辑考试草稿", description = "使用行版本更新尚未发布的考试规则")
    public R<Void> editDraft(@PathVariable Long examId, @RequestBody ExamEditDTO request) {
        request.setExamId(examId);
        return toR(examService.edit(request));
    }

    @DeleteMapping("/delete")
    @Operation(summary = "删除测试", description = "删除测试，未发布测试可删除")
    @Parameter(name = "examId", in = ParameterIn.QUERY, description = "测试ID", required = true)
    @ApiResponse(responseCode = "1000", description = "删除成功")
    @ApiResponse(responseCode = "2000", description = "测试已发布或服务异常")
    public R<Void> delete(@Parameter(description = "测试ID") Long examId) {
        return toR(examService.delete(examId));
    }

    @PutMapping("/publish")
    @Operation(summary = "发布测试", description = "发布测试，发布后会出现在用户侧测试列表并写入缓存")
    @Parameter(name = "examId", in = ParameterIn.QUERY, description = "测试ID", required = true)
    @ApiResponse(responseCode = "1000", description = "发布成功")
    @ApiResponse(responseCode = "2000", description = "测试已结束、没有题目或服务异常")
    public R<Void> publish(@Parameter(description = "测试ID") Long examId) {
        return toR(examService.publish(examId));
    }

    @PostMapping("/{examId}/publish")
    @Operation(summary = "发布不可变试卷", description = "完整校验草稿并在一个事务中生成考试和题目快照")
    public R<ExamPublicationVO> publishVersion(
            @PathVariable Long examId,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @RequestHeader(value = "X-Request-ID", required = false) String requestId) {
        return R.ok(examService.publish(examId, idempotencyKey, requestId));
    }

    @PostMapping("/{examId}/withdraw")
    @Operation(summary = "撤回考试", description = "只允许在考试开始前将已发布考试退回草稿")
    public R<Void> withdraw(@PathVariable Long examId) {
        return toR(examService.cancelPublish(examId));
    }

    @PutMapping("/cancelPublish")
    @Operation(summary = "取消发布", description = "取消测试发布，并从缓存中移除")
    @Parameter(name = "examId", in = ParameterIn.QUERY, description = "测试ID", required = true)
    @ApiResponse(responseCode = "1000", description = "取消成功")
    @ApiResponse(responseCode = "2000", description = "测试已开始或服务异常")
    public R<Void> cancelPublish(@Parameter(description = "测试ID") Long examId) {
        return toR(examService.cancelPublish(examId));
    }
}
