package com.sintao.friend.elasticsearch;

import com.sintao.friend.domain.question.es.QuestionES;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.elasticsearch.annotations.Query;
import org.springframework.data.elasticsearch.repository.ElasticsearchRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface FriendQuestionRepository extends ElasticsearchRepository<QuestionES, Long> {

    Page<QuestionES> findQuestionByDifficulty(Integer difficulty, Pageable pageable);

    //select  * from tb_question where (title like '%aaa%' or content like '%bbb%')  and difficulty = 1
    @Query("{\"bool\": {\"should\": [{ \"match\": { \"title\": \"?0\" } }, { \"match\": { \"content\": \"?1\" } }], \"minimum_should_match\": 1, \"must\": [{\"term\": {\"difficulty\": \"?2\"}}]}}")
    Page<QuestionES> findByTitleOrContentAndDifficulty(String keywordTitle, String keywordContent,Integer difficulty,  Pageable pageable);

    @Query("{\"bool\": {\"should\": [{ \"match\": { \"title\": \"?0\" } }, { \"match\": { \"content\": \"?1\" } }], \"minimum_should_match\": 1}}")
    Page<QuestionES> findByTitleOrContent(String keywordTitle, String keywordContent, Pageable pageable);

}

