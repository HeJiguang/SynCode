package com.sintao.friend.mapper.exam;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.sintao.friend.domain.exam.IntegrityEvent;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

public interface IntegrityEventMapper extends BaseMapper<IntegrityEvent> {

    @Select("select coalesce(sum(risk_points), 0) from tb_integrity_event where attempt_id = #{attemptId}")
    Integer sumRiskPointsByAttemptId(@Param("attemptId") Long attemptId);
}
