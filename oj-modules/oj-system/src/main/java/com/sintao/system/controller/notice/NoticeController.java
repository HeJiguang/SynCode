package com.sintao.system.controller.notice;

import com.sintao.common.core.controller.BaseController;
import com.sintao.common.core.domain.R;
import com.sintao.common.core.domain.TableDataInfo;
import com.sintao.system.domain.notice.dto.NoticeAddDTO;
import com.sintao.system.domain.notice.dto.NoticeEditDTO;
import com.sintao.system.domain.notice.dto.NoticeQueryDTO;
import com.sintao.system.domain.notice.vo.NoticeDetailVO;
import com.sintao.system.service.notice.INoticeService;
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
@RequestMapping("/notice")
@Tag(name = "公告管理接口")
public class NoticeController extends BaseController {

    @Autowired
    private INoticeService noticeService;

    @GetMapping("/list")
    @Operation(summary = "公告列表")
    public TableDataInfo list(NoticeQueryDTO noticeQueryDTO) {
        return getTableDataInfo(noticeService.list(noticeQueryDTO));
    }

    @PostMapping("/add")
    @Operation(summary = "新增公告")
    public R<Void> add(@RequestBody NoticeAddDTO noticeAddDTO) {
        return toR(noticeService.add(noticeAddDTO));
    }

    @GetMapping("/detail")
    @Operation(summary = "公告详情")
    @Parameter(name = "noticeId", in = ParameterIn.QUERY, required = true)
    @ApiResponse(responseCode = "1000", description = "成功返回公告详情")
    public R<NoticeDetailVO> detail(@Parameter(description = "公告ID") Long noticeId) {
        return R.ok(noticeService.detail(noticeId));
    }

    @PutMapping("/edit")
    @Operation(summary = "编辑公告")
    public R<Void> edit(@RequestBody NoticeEditDTO noticeEditDTO) {
        return toR(noticeService.edit(noticeEditDTO));
    }

    @PutMapping("/publish")
    @Operation(summary = "发布公告")
    public R<Void> publish(@Parameter(description = "公告ID") Long noticeId) {
        return toR(noticeService.publish(noticeId));
    }

    @PutMapping("/cancelPublish")
    @Operation(summary = "撤回公告")
    public R<Void> cancelPublish(@Parameter(description = "公告ID") Long noticeId) {
        return toR(noticeService.cancelPublish(noticeId));
    }

    @PutMapping("/pin")
    @Operation(summary = "设置置顶状态")
    public R<Void> pin(@Parameter(description = "公告ID") Long noticeId,
                       @Parameter(description = "是否置顶 0否 1是") Integer pinned) {
        return toR(noticeService.pin(noticeId, pinned));
    }

    @DeleteMapping("/delete")
    @Operation(summary = "删除公告")
    public R<Void> delete(@Parameter(description = "公告ID") Long noticeId) {
        return toR(noticeService.delete(noticeId));
    }
}
