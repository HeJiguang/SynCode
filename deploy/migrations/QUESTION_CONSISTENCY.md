# 题库 MySQL / ES / Redis 一致性

本次范围是题库：后台增删改、Python 导入、搜索、详情、普通练习判题、上一题/下一题、热门题目。考试仍使用现有考试版本快照。其他业务缓存和 Agent 索引不在本次范围。

## 数据流

1. `tb_question` 是唯一权威数据，详情、运行和普通判题从 MySQL 读取。一次运行复用一次查询的题目。
2. `AFTER INSERT/UPDATE/DELETE` 触发器在**原事务内**更新 `tb_question_sync_state`，并向 `tb_question_outbox` 分别写入 ES、REDIS 两条任务。后台、Python importer 和普通 SQL DML 都被覆盖，无须重复发消息。事务回滚时这三处写入全部回滚。
3. system 服务（或 compact runtime）每秒租约领取任务，发送持久化 RabbitMQ 消息。消息只包含 outbox ID，不包含题目/答案。独立 template 不改判题 producer 的回调或 converter。
4. 只有 broker confirm ACK 且没有 mandatory return 才记录 SENT。SENT 不等于同步完成；60 秒后未完成会重新投递，覆盖进程崩溃、发送结果未知、队列丢失等情况。
5. 两个独立队列消费时锁住该题状态行，读取当前版本和当前 MySQL 内容。旧消息也只投影最新数据。ES 使用 `external_gte` 版本写入；删除写永久 tombstone，所有搜索排除 `deleted=true`。
6. Redis 消费仅失效 ID 列表；同一个 Lua 脚本变更 generation 并删列表。重建前读取 generation，查询 MySQL 后写带 TTL 的临时列表，再通过 Lua 比较 generation 并原子替换。Redis Cluster 的同一列表相关键使用同一个 hash tag。
7. 投影和 MySQL 进度记录成功后才 ACK。失败先持久化重试（指数退避，上限 300 秒），再 ACK；如果持久化也失败，保持消息未确认。重复、乱序消息允许存在。
8. 每分钟对账 100 条状态，按 question ID 分页轮转：比较 ES 内容哈希，修复缺失/过期文档及丢失的当前 outbox 任务；周期性失效 Redis 列表。列表 TTL 为 300 秒。ES/Redis 各自记录进度，互不阻塞。

这是最终一致性，正常情况下为秒级；故障期间延迟取决于恢复、积压和重试。搜索可能短暂看到旧题目，但详情/判题使用 MySQL 最新内容。Redis 故障时导航和热门列表回源 MySQL。

## 部署步骤

1. 备份 MySQL、记录发布镜像和 ES 快照标识。暂停后台、importer 和修复脚本的题目写入，暂停题目搜索流量。MySQL 8 必须是 InnoDB。
2. 按迁移 README 用 Flyway 执行 `V2026102801__question_outbox.sql`，运行对应 verification 脚本。迁移账号需要 CREATE TABLE、TRIGGER 等权限；触发器 definer 在发布后仍需有效。初始回填为全量 SQL，大题库先在副本估算时间、日志量和维护窗口。
3. 停止所有旧版本题库应用，确保旧的直接 ES 写入和读时重建逻辑不再运行。部署本版本，先保持 `QUESTION_SYNC_ENABLED=false`。触发器已捕获新写入，但建议完成以下步骤后再恢复写入。
4. **首次需要在维护窗口重新建立 `idx_question`**：旧索引的内部 `_version` 无法直接当作 MySQL revision；旧的孤立文档也需要清除。先做 ES 快照，核验当前环境，再通过运维流程删除/重建这个派生索引（保留现有字段映射，新增 `revision:long`、`deleted:boolean`、`contentHash:keyword`）。不要删除 MySQL 数据。也可在后续发布中设计新索引加 alias 的无停机迁移；本次采用明确维护窗口。
5. system/compact 启用 `QUESTION_SYNC_ENABLED=true`。RabbitMQ 设置 `publisher-confirm-type: correlated`、`publisher-returns: true`；system local 配置已补齐连接环境变量，runtime 已有这些配置。分布式部署必须为 system 配置可用 RabbitMQ 地址/账号。只在 system 或包含 system 的 runtime 上启用，不能运行两套旧/新写路径。
6. 启动后让 repository 创建/核验映射并消费基线任务。观察两类任务全部到 DONE，ES 活题目数与 MySQL 对应，详情、判题、导航和热门列表冒烟通过。
7. 恢复题目写入和搜索流量，验证新增、修改、删除各一条。随后观察积压年龄、失败次数、ES/Redis 版本落后、数据库锁等待以及应用延迟。

触发器约束：不支持 `TRUNCATE tb_question`、绕开触发器的数据导入、修改 question_id。数据恢复或换库必须重新核验状态/消息；不要仅还原 `tb_question` 或重置 revision 后继续写旧 ES 索引。

Redis 列表键改为 `q:{navigation}:list` 和 `q:{hot}:list`；旧 `q:l`、`q:h:l` 不再读取，可在确认所有旧实例停止后人工清理。generation 键保留，避免过期后接受旧 generation；临时键自动过期。

## 观察与人工恢复

```sql
SELECT target,status,COUNT(*) AS events,MIN(created_at) AS oldest,
       MAX(attempts) AS max_attempts
FROM tb_question_outbox GROUP BY target,status;

SELECT id,question_id,target,attempts,last_error,available_at
FROM tb_question_outbox WHERE status<>'DONE'
ORDER BY created_at,id LIMIT 100;

SELECT question_id,revision,es_revision,redis_revision,deleted
FROM tb_question_sync_state
WHERE es_revision<revision OR redis_revision<revision
ORDER BY updated_at LIMIT 100;
```

失败记录无限保留并持续重试，不因达到次数上限而静默丢弃；对高 attempts/长时间积压告警。不要删除当前 revision 的任务，对账依赖它们。历史 DONE 任务的归档/保留期限应按部署数据量另行制定。

故障排除后，可通过受控运维 SQL 立即重放某个题目的两个最新任务（参数为实际题目 ID）：

```sql
UPDATE tb_question_outbox o JOIN tb_question_sync_state s
ON o.question_id=s.question_id AND o.revision=s.revision
SET o.status='PENDING',o.available_at=UTC_TIMESTAMP(3),o.lease_token=NULL
WHERE o.question_id = /* 题目 ID */ 123;
```

全量重放使用相同 JOIN 去掉单题条件，需分批执行以限制积压。日常对账不负责扫描未知来源额外写入的 ES 孤立文档；必须禁止绕过此链路的 ES 写入。发现这种情况使用维护窗口的全量索引重建流程。

回滚优先关闭同步开关、暂停题目写入、保留表/触发器/任务，按配套 rollback 说明恢复。不要同时运行旧的无版本 ES 写入器。不能通过清空 outbox 解决积压。

## 验证与故障演练

```powershell
mvn -pl oj-modules/oj-system,oj-modules/oj-friend,oj-modules/oj-job -am test
python deploy/test/question_sync_mysql.py --mysql-bin E:/develop/mysql-8.0.34-winx64/bin
mvn -pl oj-common/oj-common-redis -am test '-Dquestion.test.redis-server=E:/develop/Redis/redis-server.exe'
```

MySQL 脚本启动临时实例，不连接已有数据库；验证迁移、基线、导入写入、回滚、并发版本、物理删除/重新插入和租约领取。Redis 实例测试只在明确指定 native server 时执行，使用临时端口和目录；验证序列化、原子替换、generation 竞争、TTL 和空结果。

Java 测试覆盖 broker ACK/NACK/return 分支、失败持久化与 ACK 顺序、数据库失败时不 ACK、旧事件读取最新版本和删除 tombstone、MySQL 详情/判题路径。

在有完整中间件的测试环境，还应执行以下发布验收：停 RabbitMQ 后修改题目并重启；停 ES 时确认 Redis 独立失效；停 Redis 时确认详情/判题与导航回源；重复/倒序投递事件；在投影成功但 ACK 前杀消费者；删除 ES 文档后等待对账修复；两实例竞争领取同一批任务。确认最终版本、活题目数、任务状态和无题目复活。
