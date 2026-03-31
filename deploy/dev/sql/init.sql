账号   密码


表名小写  多个单词 下划线隔开  全部以tb开头
create table tb_sys_user (
user_id      bigint unsigned not null comment '用户id（主键）',
user_account varchar(20) not null  comment '账号',
nick_name    varchar(20) comment '昵称',
password     char(60) not null  comment '密码',
create_by    bigint unsigned not null  comment '创建人',
create_time  datetime not null comment '创建时间',
update_by    bigint unsigned  comment '更新人',
update_time  datetime comment '跟新时间',
primary key (`user_id`),
unique key `idx_user_account` (`user_account`)
);

字符串：char varchar  区别：
char 定长 char(10)
varchar 动态开辟空间  varchar(10)


追踪数据创建、修改的历史寻找责任人



--题库管理

B端：列表功能、添加题目、编辑、删除


C端：题库列表功能、题目热榜列表、答题、竞赛开始答题、竞赛练习
题目数据      ----》数据库  mysql    设计表结构
满足需求  避免冗余设计  考虑今后发展
题目内容： 长度变化
两数之和  1 + 2 = 3

[
    {
        "input": "1 2",
        "output": "3"
    },
    {
        "input": "4 5",
        "output": "9"
    }
]
时间限制 ：毫秒    空间限制：字节
delete  from  tb_question where question_id =
create table tb_question(
question_id bigint unsigned not null comment '题目id',
title varchar(50) not null  comment '题目标题',
difficulty tinyint not null comment '题目难度1:简单  2：中等 3：困难',
time_limit int not null comment '时间限制',
space_limit int not null comment '空间限制',
content varchar(1000) not null comment '题目内容',
question_case varchar(1000)  comment '题目用例',
default_code varchar(500) not null comment '默认代码块',
main_fuc varchar(500) not null comment 'main函数',
create_by    bigint unsigned not null  comment '创建人',
create_time  datetime not null comment '创建时间',
update_by    bigint unsigned  comment '更新人',
update_time  datetime comment '更新时间',
primary key(`question_id`)
);






--竞赛管理
B端：列表、新增、编辑、删除、发布、撤销发布

C端：列表（未开始、历史） 、报名参赛、我的比赛、参加竞赛（竞赛倒计时、竞赛内题目切换、完成竞赛） 、竞赛练习、查看排名、我的消息
是否开赛 不需要加在数据库中，我们实时计算就可以
报名参赛：未开始、未报名
create table tb_exam (
exam_id  bigint unsigned not null comment '竞赛id（主键）',
title varchar(50) not null comment '竞赛标题',
start_time datetime not null comment '竞赛开始时间',
end_time datetime not null comment '竞赛结束时间',
status tinyint not null default '0' comment '是否发布 0：未发布  1：已发布',
--exam_question   这个竞赛下所有的题目都存进来并且用&分隔开   10
create_by    bigint unsigned not null  comment '创建人',
create_time  datetime not null comment '创建时间',
update_by    bigint unsigned  comment '更新人',
update_time  datetime comment '更新时间',
primary key(exam_id)
)

题目和竞赛之间是多对一的关系
题目和竞赛的关系表
题目id：  1    2   3  4
竞赛id：999
记录1： 主键id   1    999
记录2： 主键id   2    999
记录3： 主键id   3    999
记录3： 主键id   4    999
select * from  tb_exam_question   where exam_id = 1;
delete  from tb_exam_question where exam_id = 1;
create table tb_exam_question (
exam_question_id  bigint unsigned not null comment '竞赛题目关系id（主键）',
question_id  bigint unsigned not null comment '题目id（主键）',
exam_id  bigint unsigned not null comment '竞赛id（主键）',
question_order int not null comment '题目顺序',
create_by    bigint unsigned not null  comment '创建人',
create_time  datetime not null comment '创建时间',
update_by    bigint unsigned  comment '更新人',
update_time  datetime comment '更新时间',
primary key(exam_question_id)
)













-- 用户管理（C端）
-- B端：列表、修改用户状态


-- C端：登录、注册、退出登录、个人中心

create table tb_user(
user_id  bigint unsigned NOT NULL COMMENT '用户id（主键）',
nick_name varchar(20) comment '用户昵称',
head_image varchar(100) comment '用户头像',
sex tinyint comment '用户状态1: 男  2：女',
phone char(11) not null comment '手机号',
code  char(6) comment '验证码',
email varchar(20) comment '邮箱',
wechat varchar(20) comment '微信号',
--AAAA  varchar(50) comment '学校/专业',  学校  & 专业
school_name  varchar(20) comment '学校',
major_name  varchar(20) comment '专业',
introduce varchar(100) comment '个人介绍',
status tinyint not null comment '用户状态0: 拉黑  1：正常',
create_by    bigint unsigned not null  comment '创建人',
create_time  datetime not null comment '创建时间',
update_by    bigint unsigned  comment '更新人',
update_time  datetime comment '更新时间',
primary key(`user_id`)
)



竞赛报名：
create table tb_user_exam(
user_exam_id bigint unsigned NOT NULL COMMENT '用户竞赛关系id',
user_id bigint unsigned NOT NULL COMMENT '用户id',
exam_id bigint unsigned NOT NULL COMMENT '竞赛id',
score int unsigned COMMENT '得分',
exam_rank  int unsigned COMMENT '排名',
create_by    bigint unsigned not null  comment '创建人',
create_time  datetime not null comment '创建时间',
update_by    bigint unsigned  comment '更新人',
update_time  datetime comment '更新时间',
primary key(user_exam_id)
)

select * from tb_user_exam where exam_id = 1  and  user_id = 100;

select user_id from tb_user_exam where exam_id = 1;

select exam_id from tb_user_exam where user_id = 100;






用户提交表
create table tb_user_submit(
submit_id bigint unsigned NOT NULL COMMENT '提交记录id',
request_id varchar(64) NOT NULL COMMENT '异步判题请求id',
user_id   bigint unsigned NOT NULL COMMENT '用户id',
question_id  bigint unsigned NOT NULL COMMENT '题目id',
exam_id bigint unsigned  COMMENT '竞赛id',
program_type tinyint NOT NULL COMMENT '代码类型 0 java   1 CPP',
user_code   text NOT NULL COMMENT '用户代码',
pass tinyint NOT NULL COMMENT '0：未通过 1：通过 2：未提交 3：判题中',
exe_message  varchar(500) NOT NULL COMMENT '执行结果',
score int NOT NULL DEFAULT '0' COMMENT '得分',
case_judge_res text COMMENT '用例评测结果',
use_time bigint COMMENT '运行耗时(ms)',
use_memory bigint COMMENT '运行内存(KB)',
judge_status tinyint NOT NULL DEFAULT '0' COMMENT '异步判题状态 0：等待 1：成功 2：死信 3：投递失败',
retry_count int NOT NULL DEFAULT '0' COMMENT '重试次数快照',
last_error varchar(1000) COMMENT '最终错误摘要',
finish_time datetime COMMENT '最终完成时间',
create_by    bigint unsigned not null  comment '创建人',
create_time  datetime not null comment '创建时间',
update_by    bigint unsigned  comment '更新人',
update_time  datetime comment '更新时间',
primary key(`submit_id`),
unique key `uk_request_id` (`request_id`),
key `idx_user_question_exam_create` (`user_id`,`question_id`,`exam_id`,`create_time`)
) DEFAULT CHARSET=utf8mb4 COMMENT '用户提交表'



我的消息功能

站内信：网站内部的一种通信方式。
 1.用户和用户之间的通信。（点对点）
 2.管理员/系统  和 某个用户之间的通信。（点对点）  ===》竞赛结果的通信消息
 3. 管理员/系统 和 某个用户群（指的是满足某一条件的用户的群体）之间的通信。（点对面）

1W

数据库表的设计

主键id  消息标题  消息内容  接收人    发送人
1      福利信息   内容      1         0
1      福利信息   内容      2         0
1      福利信息   内容      3         0
.........

消息内容表
create table tb_message_text(
text_id  bigint unsigned NOT NULL COMMENT '消息内容id（主键）',
message_title varchar(10)  NOT NULL COMMENT '消息标题',
message_content varchar(200)  NOT NULL COMMENT '消息内容',
create_by    bigint unsigned not null  comment '创建人',
create_time  datetime not null comment '创建时间',
update_by    bigint unsigned  comment '更新人',
update_time  datetime comment '更新时间',
primary key (text_id)
)



消息表
create table tb_message(
message_id  bigint unsigned NOT NULL COMMENT '消息id（主键）',
text_id  bigint unsigned NOT NULL COMMENT '消息内容id（主键）',
send_id  bigint unsigned NOT NULL COMMENT '消息发送人id',
rec_id  bigint unsigned NOT NULL COMMENT '消息接收人id',
create_by    bigint unsigned not null  comment '创建人',
create_time  datetime not null comment '创建时间',
update_by    bigint unsigned  comment '更新人',
update_time  datetime comment '更新时间',
primary key (message_id)
)

create table tb_notice(
notice_id bigint unsigned NOT NULL COMMENT '公告id',
title varchar(100) NOT NULL COMMENT '公告标题',
content text NOT NULL COMMENT '公告正文',
category varchar(32) NOT NULL DEFAULT '公告' COMMENT '公告分类',
is_public tinyint NOT NULL DEFAULT '1' COMMENT '是否公共可见 0否 1是',
is_pinned tinyint NOT NULL DEFAULT '0' COMMENT '是否置顶 0否 1是',
status tinyint NOT NULL DEFAULT '0' COMMENT '状态 0草稿 1已发布',
publish_time datetime COMMENT '发布时间',
create_by    bigint unsigned not null  comment '创建人',
create_time  datetime not null comment '创建时间',
update_by    bigint unsigned  comment '更新人',
update_time  datetime comment '更新时间',
primary key (notice_id),
key idx_notice_public_publish (is_public, status, publish_time),
key idx_notice_pinned_publish (is_pinned, publish_time)
) DEFAULT CHARSET=utf8mb4 COMMENT '系统公告表'





















































