package com.sintao.friend.domain.exam.vo;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public class IntegrityBatchResultVO {
    private int accepted;
    private int duplicates;
    private int riskPoints;
}
