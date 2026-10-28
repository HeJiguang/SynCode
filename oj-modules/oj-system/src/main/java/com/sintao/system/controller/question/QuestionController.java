package com.sintao.system.controller.question;

import com.sintao.common.core.controller.BaseController;
import com.sintao.common.core.domain.R;
import com.sintao.common.core.domain.TableDataInfo;
import com.sintao.system.domain.question.dto.QuestionAddDTO;
import com.sintao.system.domain.question.dto.QuestionEditDTO;
import com.sintao.system.domain.question.dto.QuestionQueryDTO;
import com.sintao.system.domain.question.vo.QuestionDetailVO;
import com.sintao.system.service.question.IQuestionService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.enums.ParameterIn;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/question")
@Tag(name = "题目管理接口")
public class QuestionController extends BaseController {

    @Autowired
    private IQuestionService questionService;

    @GetMapping("/list")
    @Operation(summary = "题目列表", description = "分页查询题目列表，支持排除指定题目 ID 等条件")
    @ApiResponse(responseCode = "200", description = "成功返回分页数据")
    public TableDataInfo list(QuestionQueryDTO questionQueryDTO) {
        return getTableDataInfo(questionService.list(questionQueryDTO));
    }

    @PostMapping("/add")
    @Operation(summary = "新增题目", description = "新增一道题目，标题不可与已有题目重复")
    @ApiResponse(responseCode = "1000", description = "新增成功")
    @ApiResponse(responseCode = "2000", description = "服务繁忙，请稍后重试")
    public R<Void> add(@RequestBody QuestionAddDTO questionAddDTO) {
        return toR(questionService.add(questionAddDTO));
    }

    @GetMapping("/detail")
    @Operation(summary = "题目详情", description = "根据题目ID获取题目详情")
    @Parameter(name = "questionId", in = ParameterIn.QUERY, description = "题目ID", required = true)
    @ApiResponse(responseCode = "1000", description = "成功返回题目详情")
    @ApiResponse(responseCode = "2000", description = "题目不存在或服务异常")
    public R<QuestionDetailVO> detail(@Parameter(description = "题目ID") Long questionId) {
        return R.ok(questionService.detail(questionId));
    }

    @PutMapping("/edit")
    @Operation(summary = "编辑题目", description = "根据题目ID更新题目信息")
    @ApiResponse(responseCode = "1000", description = "编辑成功")
    @ApiResponse(responseCode = "2000", description = "题目不存在或服务异常")
    public R<Void> edit(@RequestBody QuestionEditDTO questionEditDTO) {
        return toR(questionService.edit(questionEditDTO));
    }

    @DeleteMapping("/delete")
    @Operation(summary = "删除题目", description = "根据题目 ID 删除题目，搜索与缓存异步同步")
    @Parameter(name = "questionId", in = ParameterIn.QUERY, description = "题目ID", required = true)
    @ApiResponse(responseCode = "1000", description = "删除成功")
    @ApiResponse(responseCode = "2000", description = "题目不存在或服务异常")
    public R<Void> delete(@Parameter(description = "题目ID") Long questionId) {
        return toR(questionService.delete(questionId));
    }
}

