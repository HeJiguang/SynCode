USE bitoj_dev;

ALTER TABLE tb_user_submit
    ADD COLUMN use_time bigint NULL COMMENT '运行耗时(ms)' AFTER case_judge_res,
    ADD COLUMN use_memory bigint NULL COMMENT '运行内存(KB)' AFTER use_time;

CREATE TABLE IF NOT EXISTS tb_notice (
    notice_id bigint unsigned NOT NULL COMMENT '公告id',
    title varchar(100) NOT NULL COMMENT '公告标题',
    content text NOT NULL COMMENT '公告正文',
    category varchar(32) NOT NULL DEFAULT '公告' COMMENT '公告分类',
    is_public tinyint NOT NULL DEFAULT 1 COMMENT '是否公共可见 0否 1是',
    is_pinned tinyint NOT NULL DEFAULT 0 COMMENT '是否置顶 0否 1是',
    status tinyint NOT NULL DEFAULT 0 COMMENT '状态 0草稿 1已发布',
    publish_time datetime NULL COMMENT '发布时间',
    create_by bigint unsigned NOT NULL COMMENT '创建人',
    create_time datetime NOT NULL COMMENT '创建时间',
    update_by bigint unsigned NULL COMMENT '更新人',
    update_time datetime NULL COMMENT '更新时间',
    PRIMARY KEY (notice_id),
    KEY idx_notice_public_publish (is_public, status, publish_time),
    KEY idx_notice_pinned_publish (is_pinned, publish_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统公告表';

INSERT INTO tb_notice (
    notice_id,
    title,
    content,
    category,
    is_public,
    is_pinned,
    status,
    publish_time,
    create_by,
    create_time
)
SELECT
    text_id,
    message_title,
    message_content,
    '公告',
    1,
    0,
    1,
    create_time,
    create_by,
    create_time
FROM tb_message_text
WHERE NOT EXISTS (
    SELECT 1 FROM tb_notice notice WHERE notice.notice_id = tb_message_text.text_id
);
