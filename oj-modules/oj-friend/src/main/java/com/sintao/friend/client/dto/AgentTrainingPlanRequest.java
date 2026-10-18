package com.sintao.friend.client.dto;

import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import lombok.Data;

import java.util.ArrayList;
import java.util.List;

@Data
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class AgentTrainingPlanRequest {

    private String traceId;

    private Long userId;

    private String conversationId;

    private String userRequest;

    private String currentLevel;

    private String targetDirection;

    private Long basedOnExamId;

    private Integer preferredCount;

    private List<SubmissionSnapshot> recentSubmissions = new ArrayList<>();

    private List<QuestionCandidate> candidateQuestions = new ArrayList<>();

    private List<ExamCandidate> candidateExams = new ArrayList<>();

    @Data
    @JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
    public static class SubmissionSnapshot {
        private Long submitId;
        private Long questionId;
        private Long examId;
        private String title;
        private Integer difficulty;
        private String algorithmTag;
        private String knowledgeTags;
        private Integer pass;
        private Integer score;
        private String exeMessage;
    }

    @Data
    @JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
    public static class QuestionCandidate {
        private Long questionId;
        private String title;
        private Integer difficulty;
        private String algorithmTag;
        private String knowledgeTags;
        private Integer estimatedMinutes;
    }

    @Data
    @JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
    public static class ExamCandidate {
        private Long examId;
        private String title;
        private String startTime;
        private String endTime;
    }
}
