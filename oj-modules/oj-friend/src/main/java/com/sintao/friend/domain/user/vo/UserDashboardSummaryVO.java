package com.sintao.friend.domain.user.vo;

import lombok.Getter;
import lombok.Setter;

import java.util.List;

@Getter
@Setter
public class UserDashboardSummaryVO {

    private Integer solvedCount;

    private Integer submissionCount;

    private Integer streakDays;

    private List<UserHeatmapPointVO> heatmap;
}
