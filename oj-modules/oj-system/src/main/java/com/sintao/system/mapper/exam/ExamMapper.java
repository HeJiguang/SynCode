package com.sintao.system.mapper.exam;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.sintao.system.domain.exam.Exam;
import com.sintao.system.domain.exam.dto.ExamQueryDTO;
import com.sintao.system.domain.exam.vo.ExamVO;

import java.util.List;

public interface ExamMapper extends BaseMapper<Exam> {

    List<ExamVO> selectExamList(ExamQueryDTO examQueryDTO);

    Exam selectByIdForUpdate(Long examId);

}

