package com.sintao.system.mapper.exam;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.sintao.system.domain.exam.ExamAttempt;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

public interface ExamAttemptMapper extends BaseMapper<ExamAttempt> {
    @Select("select * from tb_exam_attempt where attempt_id = #{attemptId} for update")
    ExamAttempt selectByIdForUpdate(@Param("attemptId") Long attemptId);
}
