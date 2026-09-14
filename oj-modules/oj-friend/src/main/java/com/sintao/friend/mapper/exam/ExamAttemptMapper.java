package com.sintao.friend.mapper.exam;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.sintao.friend.domain.exam.ExamAttempt;

public interface ExamAttemptMapper extends BaseMapper<ExamAttempt> {
    ExamAttempt selectByIdForUpdate(Long attemptId);
}
