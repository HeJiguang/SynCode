package com.sintao.api;

import com.sintao.common.core.constants.Constants;
import com.sintao.common.core.domain.TableDataInfo;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;

/**
 * 题目服务 Feign 接口，供网关后的 Python agent runtime 等调用方按关键词检索题目。
 */
@FeignClient(contextId = "RemoteQuestionService", value = Constants.FRIEND_SERVICE)
public interface RemoteQuestionService {

    /**
     * 分页查询题目列表，支持关键词和难度筛选，对齐友端 `/question/semiLogin/list`。
     *
     * @param keyword 关键词，匹配标题和内容，可为空
     * @param difficulty 难度 1/2/3，可为空
     * @param pageNum 页码，从 1 开始
     * @param pageSize 每页条数
     */
    @GetMapping("/question/semiLogin/list")
    TableDataInfo list(
            @RequestParam(value = "keyword", required = false) String keyword,
            @RequestParam(value = "difficulty", required = false) Integer difficulty,
            @RequestParam(value = "pageNum", defaultValue = "1") Integer pageNum,
            @RequestParam(value = "pageSize", defaultValue = "10") Integer pageSize
    );
}
