package com.sintao.system.manager;

import com.sintao.common.core.constants.CacheConstants;
import com.sintao.common.redis.service.RedisService;
import com.sintao.system.domain.exam.Exam;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Component
public class ExamCacheManager {

    @Autowired
    private RedisService redisService;

    public void addCache(Exam exam) {
        redisService.leftPushForList(getExamListKey(), exam.getExamId());
        redisService.setCacheObject(getDetailKey(exam.getExamId()), exam);
    }

    public void deleteCache(Long examId) {
        redisService.removeForList(getExamListKey(), examId);
        redisService.deleteObject(getDetailKey(examId));
        redisService.deleteObject(getExamQuestionListKey(examId));
    }

    public void deleteUserExamList(Long userId) {
        redisService.deleteObject(CacheConstants.USER_EXAM_LIST + userId);
    }

    private String getExamListKey() {
        return CacheConstants.EXAM_UNFINISHED_LIST;
    }

    private String getDetailKey(Long examId) {
        return CacheConstants.EXAM_DETAIL + examId;
    }

    private String getExamQuestionListKey(Long examId) {
        return CacheConstants.EXAM_QUESTION_LIST + examId;
    }
}

