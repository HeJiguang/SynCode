package com.sintao.system.domain.exam.dto;

import lombok.Getter;
import lombok.Setter;

import java.util.List;

@Getter
@Setter
public class ExamQuestionsReplaceDTO {

    private List<ExamQuestionItemDTO> questions;
}
