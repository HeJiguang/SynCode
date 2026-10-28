package com.sintao.job.handler;

import com.sintao.common.core.constants.CacheConstants;
import com.sintao.common.core.constants.Constants;
import com.sintao.common.redis.service.RedisService;
import com.sintao.job.mapper.user.UserSubmitMapper;
import com.github.pagehelper.PageHelper;
import com.xxl.job.core.handler.annotation.XxlJob;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.List;

@Component
@Slf4j
public class QuestionXxlJob {

    @Autowired
    private UserSubmitMapper userSubmitMapper;

    @Autowired
    private RedisService redisService;

    @XxlJob("hostQuestionListHandler")
    public void hostQuestionListHandler() {
        log.info("----- 题目热门列表统计开始 ------");
        String generation = redisService.listGeneration(CacheConstants.QUESTION_HOST_LIST);
        PageHelper.startPage(Constants.HOST_QUESTION_LIST_START, Constants.HOST_QUESTION_LIST_END);
        List<Long> questionIdList = userSubmitMapper.selectHostQuestionList();
        redisService.replaceVersionedList(CacheConstants.QUESTION_HOST_LIST, generation, questionIdList, 300);
        log.info("----- 题目热门列表统计结束 ------");
    }
}

