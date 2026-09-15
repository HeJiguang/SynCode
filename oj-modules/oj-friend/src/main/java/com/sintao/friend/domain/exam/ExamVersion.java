package com.sintao.friend.domain.exam;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;

@Getter
@Setter
@TableName("tb_exam_version")
public class ExamVersion {
    @TableId(value = "version_id", type = IdType.ASSIGN_ID)
    private Long versionId;
    private Long examId;
    private Integer versionNo;
    private String title;
    private String description;
    private LocalDateTime startTime;
    private LocalDateTime latestStartTime;
    private LocalDateTime endTime;
    private Integer durationMinutes;
    private String timezone;
    private Integer maxFormalSubmissions;
    private String resultReleasePolicy;
    private LocalDateTime resultReleaseTime;
    private String feedbackPolicyJson;
    private String integrityPolicyJson;
    private String contentHash;
    private Long publishedBy;
    private LocalDateTime publishedTime;
}
