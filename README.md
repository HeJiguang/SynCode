# SynCode

面向编程测评与训练场景的多模块工程项目。

当前公开版本以后端能力为主，重点放在异步判题链路、结果推送机制、训练/AI 能力探索和本地微服务协作。前端整体体验和正式线上部署仍在持续建设中，因此本仓库暂不以“完整网站成品”作为展示重点。

## 项目简介

`SynCode` 以 Java 微服务为主体，围绕编程题目管理、用户练习/提交、异步判题、结果通知和训练规划等能力展开。

目前仓库中的重点方向包括：

- 基于 Spring Boot / Spring Cloud Alibaba 的多模块后端拆分
- 基于 RabbitMQ 的异步判题主链路
- 基于 WebSocket + Redis Pub/Sub 的判题结果推送
- 基于逻辑时钟与持久化水位的趋势递增 Snowflake 主键
- 基于 Python `oj-agent` 的 AI/训练规划能力探索
- 可插拔 Agent Runtime，支持 Hermes + DeepSeek、持久会话、超时终止与 Direct 回退
- 多用户 Agent Run 准入控制，支持用户级活跃/频率限制与全局执行并发上限

## 核心模块

- `oj-gateway`
  统一网关入口，负责路由转发、鉴权过滤和对外访问入口管理。

- `oj-modules/oj-friend`
  面向用户侧的核心业务模块，承载用户提交、训练流程、WebSocket 结果推送等逻辑。

- `oj-modules/oj-judge`
  判题消费与执行模块，负责异步判题处理、结果落库和最终状态回传。

- `oj-modules/oj-system`
  系统侧与基础业务管理模块，负责题目、考试等后台能力。

- `oj-common`
  公共基础能力层，包含核心常量、安全、Redis、RabbitMQ、MyBatis、消息、文件等通用组件。

- `oj-api`
  服务间共享的 DTO、接口约定和公共传输对象定义。

- `oj-agent`
  基于 FastAPI + LangGraph 的独立 Python 服务，用于 AI 助教、训练规划等能力扩展。

## 技术栈

- Java 17
- Spring Boot 3.2.5
- Spring Cloud 2022 / Spring Cloud Alibaba / Nacos
- MyBatis-Plus
- MySQL
- Redis
- RabbitMQ
- Python 3.11+
- FastAPI
- LangGraph

## 当前进度

- 已形成多模块后端工程结构，核心业务拆分基本清晰
- 已具备异步判题链路和请求级 `requestId` 跟踪能力
- 已接入判题结果 WebSocket 推送机制
- 已纳入 Python `oj-agent` 服务用于 AI 能力探索
- 当前公开仓库以后端、本地运行和架构演进为主
- 前端整体仍在建设中，暂不作为当前仓库首页展示重点
- 暂无正式公网演示地址

## 本地运行

### 环境依赖

- JDK 17
- Maven 3.9+
- Python 3.11+（用于 `oj-agent`）
- Nacos
- MySQL
- Redis
- RabbitMQ

### 代码编译

```bash
mvn -q -DskipTests compile
```

### Java 服务启动示例

按需启动各模块，常见核心链路包括：

```bash
mvn -pl oj-modules/oj-system -am spring-boot:run
mvn -pl oj-modules/oj-friend -am spring-boot:run
mvn -pl oj-modules/oj-judge -am spring-boot:run
mvn -pl oj-gateway -am spring-boot:run
```

### Python Agent 启动示例

```bash
cd oj-agent
pip install -e .[dev]
uvicorn app.main:app --host 0.0.0.0 --port 8015
```

Hermes sidecar、DeepSeek 和安全隔离配置参见 [`docs/architecture/hermes-agent-runtime.md`](docs/architecture/hermes-agent-runtime.md)。

具体端口、Nacos 配置和本地环境参数请以各模块的 `bootstrap.yml`、`application-local.yml` 及相关本地配置文件为准。

## 后续计划

- 持续完善用户侧前端与整体交互链路
- 继续推进训练规划与 AI 能力的业务集成
- 补充更清晰的部署与运行文档
- 完善端到端联调与本地开发体验

## 说明

- 当前仓库公开名为 `SynCode`
- 代码中部分 `artifactId`、包名和历史命名仍保留 `sintao-oj` / `com.sintao` 轨迹，这是当前演进状态的一部分
- 本仓库现阶段更适合作为后端工程与本地开发项目查看，而不是完整上线产品展示
