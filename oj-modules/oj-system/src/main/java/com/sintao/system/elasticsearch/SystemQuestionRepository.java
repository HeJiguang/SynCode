package com.sintao.system.elasticsearch;

import com.sintao.system.domain.question.es.QuestionES;
import org.springframework.data.elasticsearch.repository.ElasticsearchRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface SystemQuestionRepository extends ElasticsearchRepository<QuestionES, Long> {

}

