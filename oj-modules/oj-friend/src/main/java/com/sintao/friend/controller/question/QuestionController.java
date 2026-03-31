package com.sintao.friend.controller.question;

import com.sintao.common.core.controller.BaseController;
import com.sintao.common.core.domain.R;
import com.sintao.common.core.domain.TableDataInfo;
import com.sintao.friend.domain.question.dto.QuestionQueryDTO;
import com.sintao.friend.domain.question.vo.QuestionDetailVO;
import com.sintao.friend.domain.question.vo.QuestionVO;
import com.sintao.friend.service.question.IQuestionService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.enums.ParameterIn;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/question")
@Tag(name = "C 端题目接口", description = "题目列表、详情、热榜等接口，部分接口支持半登录访问")
public class QuestionController extends BaseController {

    @Autowired
    private IQuestionService questionService;

    @GetMapping("/semiLogin/list")
    @Operation(summary = "题目列表", description = "分页查询题目列表，支持关键词搜索和难度筛选")
    @ApiResponse(responseCode = "200", description = "成功返回分页数据")
    public TableDataInfo list(QuestionQueryDTO questionQueryDTO) {
        return questionService.list(questionQueryDTO);
    }

    @GetMapping("/semiLogin/dbList")
    @Operation(summary = "题目列表（数据库版）", description = "从数据库分页查询题目列表，当前暂未实现")
    @ApiResponse(responseCode = "200", description = "成功返回分页数据")
    public TableDataInfo dbList(QuestionQueryDTO questionQueryDTO) {
        return null;
    }

    @GetMapping("/semiLogin/hotList")
    @Operation(summary = "题目热榜", description = "获取提交次数最多的 Top5 题目")
    @ApiResponse(responseCode = "200", description = "成功返回热榜题目列表")
    public R<List<QuestionVO>> hotList() {
        return R.ok(questionService.hotList());
    }

    @GetMapping("/semiLogin/detail")
    @Operation(summary = "题目详情（公开）", description = "未登录也可访问的题目详情接口，返回题面、默认代码和示例用例")
    @Parameter(name = "questionId", in = ParameterIn.QUERY, description = "题目ID", required = true)
    @ApiResponse(responseCode = "200", description = "成功返回题目详情")
    public R<QuestionDetailVO> semiLoginDetail(@Parameter(description = "题目ID") Long questionId) {
        return R.ok(questionService.detail(questionId));
    }

    @GetMapping("/detail")
    @Operation(summary = "题目详情", description = "根据题目ID获取题目完整信息")
    @Parameter(name = "questionId", in = ParameterIn.QUERY, description = "题目ID", required = true)
    @ApiResponse(responseCode = "200", description = "成功返回题目详情")
    @ApiResponse(responseCode = "2000", description = "题目不存在")
    public R<QuestionDetailVO> detail(@Parameter(description = "题目ID") Long questionId) {
        return R.ok(questionService.detail(questionId));
    }

    @GetMapping("/preQuestion")
    @Operation(summary = "上一题", description = "获取题目列表中当前题目的上一题ID，按创建时间排序")
    @Parameter(name = "questionId", in = ParameterIn.QUERY, description = "当前题目ID", required = true)
    @ApiResponse(responseCode = "200", description = "成功返回上一题ID")
    @ApiResponse(responseCode = "2000", description = "已经是第一题")
    public R<String> preQuestion(@Parameter(description = "当前题目ID") Long questionId) {
        return R.ok(questionService.preQuestion(questionId));
    }

    @GetMapping("/nextQuestion")
    @Operation(summary = "下一题", description = "获取题目列表中当前题目的下一题ID，按创建时间排序")
    @Parameter(name = "questionId", in = ParameterIn.QUERY, description = "当前题目ID", required = true)
    @ApiResponse(responseCode = "200", description = "成功返回下一题ID")
    @ApiResponse(responseCode = "2000", description = "已经是最后一题")
    public R<String> nextQuestion(@Parameter(description = "当前题目ID") Long questionId) {
        return R.ok(questionService.nextQuestion(questionId));
    }
}
