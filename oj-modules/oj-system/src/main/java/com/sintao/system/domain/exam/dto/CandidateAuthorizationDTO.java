package com.sintao.system.domain.exam.dto;

import lombok.Getter;
import lombok.Setter;

import java.util.List;

@Getter
@Setter
public class CandidateAuthorizationDTO {
    private List<Long> userIds;
    private String source;
}
