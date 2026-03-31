package com.sintao.friend.controller.message;

import com.sintao.common.core.controller.BaseController;
import com.sintao.common.core.domain.PageQueryDTO;
import com.sintao.common.core.domain.TableDataInfo;
import com.sintao.friend.service.notice.IPublicNoticeService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/message")
@Tag(name = "公共公告接口", description = "未登录也可查看的系统公共公告列表")
public class MessageController extends BaseController {

    @Autowired
    private IPublicNoticeService publicNoticeService;

    @GetMapping("/semiLogin/list")
    @Operation(summary = "公共公告列表", description = "分页获取全站公共公告")
    @ApiResponse(responseCode = "200", description = "成功返回公告列表")
    public TableDataInfo list(PageQueryDTO dto) {
        return publicNoticeService.list(dto);
    }
}
