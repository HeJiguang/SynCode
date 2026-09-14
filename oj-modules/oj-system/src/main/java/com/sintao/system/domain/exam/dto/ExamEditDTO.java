package com.sintao.system.domain.exam.dto;

import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class ExamEditDTO extends ExamAddDTO {

    private Long examId;

    private Integer expectedRowVersion;
}

