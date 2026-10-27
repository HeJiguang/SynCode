# 判题执行器

Java 服务使用 `sandbox.execution.mode=go-judge`（local/swarm 配置的默认值）。
旧 `pool` / `standalone` 保留供原有同步接口使用，不具备本方案的逐用例隔离、完整清理和测试集引用支持；不能将新格式 MQ 消息发送给旧 worker。
回滚还需要恢复旧发布端及其 Docker 挂载，不能只切换 mode；新的 Swarm 清单已经移除了 Socket/工作目录挂载。

## 部署

建议使用 Linux 5.19+（cgroup v2 的 memory.peak），确保 CPU/memory/pids controller 可用。
在专用 Linux 判题节点上，设置一个随机 `GO_JUDGE_TOKEN`，执行：

```sh
export GO_JUDGE_TOKEN='替换为随机的执行器访问令牌'
docker compose -f deploy/judge/compose.yml up -d --build
```

宿主机运行 Java 服务时配置：

```text
SANDBOX_EXECUTION_MODE=go-judge
GO_JUDGE_ENDPOINT=http://127.0.0.1:5050
GO_JUDGE_TOKEN=与执行器一致
GO_JUDGE_PARALLELISM=4
```

Docker 中的 Java worker 应加入 `syncode-judge-execution` 网络，使用 `http://go-judge:5050`。
跨节点/Swarm 应在专用可信网络上提供可达的执行器地址，设置 `GO_JUDGE_ENDPOINT`，不能直接假设 Compose DNS 可跨节点解析。
API 不发布到公网。Java 服务无需挂载 Docker Socket 或宿主工作目录。不要把数据库等应用环境变量传给执行器。

外层 supervisor 使用 privileged 来管理 Linux namespace/cgroup；用户程序在内层隔离环境运行，UID/GID=1536，不共享 supervisor 网络。
`mount.yaml` 只开放镜像内的只读编译/运行依赖和设备，`/w`、`/tmp` 使用各 128 MiB 的 tmpfs；不挂载标准答案、宿主目录、密码或 Docker Socket。
保持 go-judge 默认 seccomp，不启用 `net-share` 或 `no-seccomp`。`no-fallback` 确保 cgroup 不可用时启动失败，而非降级执行。

部署前按节点容量设置并发；每并发需预留题目内存额度、tmpfs、输出缓存和执行器开销。最大题目额度是准入上限，不是预留内存。
需要更大临时区时修改镜像中的 mount 配置并重建；不能用增大内存上限来假装扩大 tmpfs。

## 数据与执行

* 异步发布先把每个用例分别 gzip/base64 编码保存到 Redis hash。SHA-256 内容摘要标识用例版本，完成后原子 rename；MQ 只携带版本、数量和提交信息。
* 测试集默认保留 168 小时，启动判题时续期。Redis 应持久化、使用符合容量规划的淘汰策略；最长排队和重试周期必须小于 TTL。缺失用例会报系统错误，不会误判通过。
* 限制：最多 10000 用例、单例 JSON 32 MiB、集合原始 JSON 合计 128 MiB，可通过 `judge.cases.*` 调整。源题库仍以原有 JSON 保存；本次未改成对象存储。
* 编译一次，编译产物在执行器文件缓存中保存。Java 打成包含内部类的 jar；C++/Go 保存可执行文件；Python 保存 pyc。
* 每例以 `copyIn` 获得编译产物的独立副本，stdin 保留原始空白并读到 EOF。副本即使被修改也不会改变缓存原件或下一用例。
* 每例使用新的用户进程/JVM。go-judge 终止残留进程并回收，清空 tmpfs 后复用环境；Reset 失败则销毁。不复用 JVM，不靠删除代码目录冒充进程回收。
* 输出留在执行器，Java 下载当前用例到有上限的临时文件，校验完整输出后删除两端文件。编译缓存在整次提交 finally 释放，15 分钟文件 TTL 处理断连/服务崩溃后的孤儿文件。
* HTTP 断连不代表程序立即结束：服务器端 CPU/墙钟限制仍然生效。不会回退到宿主执行。当前 REST 版本未提供按提交即时取消协议。

## 限额与判定

题目 `timeLimit` 使用毫秒 CPU 时间，`spaceLimit` 使用 KiB 的执行单元内存（包含 JVM 等开销）。默认墙钟预算是 CPU 时间的 3 倍。
每题最多 60 秒、2 GiB；超过平台准入上限会报配置错误，不会偷偷截小题目额度。
编译独立使用 30 秒 CPU / 512 MiB。总提交预算随用例数量计算，最多 10 分钟，包含编译、下载、校验。
这些是可配置的平台初值，不是 LeetCode 官方限制或已经完成 Hot100 全量压测的结论。

`sandbox.go-judge` 还支持：`process-limit=64`、`cpu-rate-limit=1000`（1 核速率）、`output-limit-bytes=33554432`（每例 stdout）、
`total-output-limit-bytes=268435456`、`artifact-limit-bytes=67108864`、`checker-time-ms=10000`。
stderr 独立限制 64 KiB，并计入提交总输出预算。达到输出上限由执行器终止，不仅截断后端字符串。
Java 最大堆设置为题目总内存的 60%，余量供 JVM 使用；需要用真实语言/题库验证，不使用 RLIMIT_AS/DATA 限制 JVM 地址空间。

普通提交在第一个错例停止；样例运行在答案错误后继续，执行错误/超限停止。
每个结果包含稳定 `caseId`；串行执行不需要 HashMap，未来并行时必须用 ID 关联，按清单顺序展示。
默认最多保存 200 条详情，各输入/答案/实际输出预览最多 2048 字符；错例替换最后一条，确保可见。
预览截断不参与判定。详情只代表已展示用例，不能再通过详情条数推断总用例数量。

题目管理端的 `gradingConfigJson` 可设置：

```json
{"checker":"unorderedTriples"}
```

支持 `text`（默认，统一 CRLF、忽略首尾空白）、`exact`、`tokens`、`unorderedLines`（保留重复次数）、`unorderedTriples`。
三元组支持 JSON 二维数组或每行三个整数，空答案用 `[]` 或 `EMPTY`。组内和组间顺序不影响结果，用户重复三元组判错。
Hot100 导入脚本为 `3sum` 配置该规则；已有题目需重新导入或在管理端更新。旧 ES 文档缺规则时回查数据库，考试使用试卷版本中的规则。
其他需要多解或无序语义的题目必须显式配置/扩展 Checker，不根据标题猜测规则。
`V2026102701__three_sum_output_checker.sql` 为已有、带 Hot100 sourceId=15 元数据且未配置 checker 的题目补齐规则；保留已有显式规则，不修改考试快照。
Java 内置 Checker 在单个 worker 内串行运行，避免大标准答案同时创建多个哈希表；校验超时作为系统错误处理，不误报用户答案错误。

## 发布与验证

先按项目迁移流程应用上述规则迁移，部署执行器并完成下面的 Linux 实测，再部署支持引用的 judge worker，最后部署新的 friend 发布端。
滚动升级时必须避免旧 worker 消费新格式消息；应排空旧队列或整体切换对应 consumer。不应只升级发布端。

```sh
GO_JUDGE_ENDPOINT=http://127.0.0.1:5050 python deploy/judge/smoke.py
```

该检查覆盖多语言编译、输入 EOF、编译缓存重复使用、超时、输出超限和正常/异常结束后的临时区重置。
Java 单元测试使用模拟执行器验证协议、配额、逐例校验和文件释放，不等于验证了 Linux 内核实际隔离效果。
