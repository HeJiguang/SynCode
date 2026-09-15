-- Read-only checks required before baselining an existing SynCode database.
-- Every query must return zero rows unless it explicitly returns a count.

SELECT required.table_name AS missing_table
FROM (
    SELECT 'tb_exam' AS table_name
    UNION ALL SELECT 'tb_exam_question'
    UNION ALL SELECT 'tb_question'
    UNION ALL SELECT 'tb_user'
    UNION ALL SELECT 'tb_user_exam'
    UNION ALL SELECT 'tb_user_submit'
) required
LEFT JOIN information_schema.tables existing
    ON existing.table_schema = DATABASE()
    AND existing.table_name = required.table_name
WHERE existing.table_name IS NULL;

SELECT exam_id, status AS invalid_status
FROM tb_exam
WHERE status NOT IN (0, 1);

SELECT exam_id, start_time, end_time
FROM tb_exam
WHERE start_time IS NULL OR end_time IS NULL OR start_time >= end_time;

SELECT exam_id, question_id, COUNT(*) AS duplicate_count
FROM tb_exam_question
GROUP BY exam_id, question_id
HAVING COUNT(*) > 1;

SELECT exam_id, question_order, COUNT(*) AS duplicate_count
FROM tb_exam_question
GROUP BY exam_id, question_order
HAVING COUNT(*) > 1;

SELECT exam_id, user_id, COUNT(*) AS duplicate_count
FROM tb_user_exam
GROUP BY exam_id, user_id
HAVING COUNT(*) > 1;

SELECT relation.exam_question_id, relation.exam_id, relation.question_id
FROM tb_exam_question relation
LEFT JOIN tb_exam exam ON exam.exam_id = relation.exam_id
LEFT JOIN tb_question question ON question.question_id = relation.question_id
WHERE exam.exam_id IS NULL OR question.question_id IS NULL;

SELECT registration.user_exam_id, registration.exam_id, registration.user_id
FROM tb_user_exam registration
LEFT JOIN tb_exam exam ON exam.exam_id = registration.exam_id
LEFT JOIN tb_user candidate ON candidate.user_id = registration.user_id
WHERE exam.exam_id IS NULL OR candidate.user_id IS NULL;
