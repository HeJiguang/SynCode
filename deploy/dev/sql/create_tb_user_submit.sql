USE bitoj_dev;

CREATE TABLE IF NOT EXISTS tb_user_submit (
  submit_id bigint unsigned NOT NULL COMMENT '提交记录id',
  request_id varchar(64) NOT NULL COMMENT '异步判题请求id',
  user_id bigint unsigned NOT NULL COMMENT '用户id',
  question_id bigint unsigned NOT NULL COMMENT '题目id',
  exam_id bigint unsigned COMMENT '竞赛id',
  program_type tinyint NOT NULL COMMENT '代码类型 0 java 1 CPP',
  user_code text NOT NULL COMMENT '用户代码',
  pass tinyint NOT NULL COMMENT '0未通过 1通过 2未提交 3判题中',
  exe_message varchar(500) NOT NULL COMMENT '执行结果',
  score int NOT NULL DEFAULT 0 COMMENT '得分',
  case_judge_res text COMMENT '用例评测结果',
  use_time bigint COMMENT '运行耗时(ms)',
  use_memory bigint COMMENT '运行内存(KB)',
  judge_status tinyint NOT NULL DEFAULT 0 COMMENT '异步判题状态 0等待 1成功 2死信 3投递失败',
  retry_count int NOT NULL DEFAULT 0 COMMENT '重试次数快照',
  last_error varchar(1000) COMMENT '最终错误摘要',
  finish_time datetime COMMENT '最终完成时间',
  create_by bigint unsigned NOT NULL COMMENT '创建人',
  create_time datetime NOT NULL COMMENT '创建时间',
  update_by bigint unsigned COMMENT '更新人',
  update_time datetime COMMENT '更新时间',
  PRIMARY KEY (submit_id),
  UNIQUE KEY uk_request_id (request_id),
  KEY idx_user_question_exam_create (user_id, question_id, exam_id, create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT '用户提交表';
