package com.sintao.system.service.exam;

import com.sintao.system.domain.exam.dto.ExamAddDTO;
import com.sintao.system.domain.exam.dto.ExamEditDTO;
import com.sintao.system.domain.exam.dto.ExamQueryDTO;
import com.sintao.system.domain.exam.dto.ExamQuestAddDTO;
import com.sintao.system.domain.exam.dto.ExamQuestionsReplaceDTO;
import com.sintao.system.domain.exam.vo.ExamDetailVO;
import com.sintao.system.domain.exam.vo.ExamPublicationVO;
import com.sintao.system.domain.exam.vo.ExamVO;

import java.util.List;

public interface IExamService {

    List<ExamVO> list(ExamQueryDTO examQueryDTO);

    String add(ExamAddDTO examAddDTO);

    boolean questionAdd(ExamQuestAddDTO examQuestAddDTO);

    boolean replaceQuestions(Long examId, ExamQuestionsReplaceDTO request);

    int questionDelete(Long examId, Long questionId);

    ExamDetailVO detail(Long examId);

    int edit(ExamEditDTO examEditDTO);

    int delete(Long examId);

    int publish(Long examId);

    ExamPublicationVO publish(Long examId, String idempotencyKey, String requestId);

    int cancelPublish(Long examId);
}

