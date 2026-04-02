# OnlineOJ Production Deploy Guide

这份文档对应你当前的真实目标环境，不是假想环境。

- Swarm manager: `101.96.200.76`
- Swarm worker: `101.96.200.77`
- 中间件现状:
  - manager: `mysql`, `redis`, `rabbitmq`, `nacos`
  - worker: `elasticsearch`, `qdrant`
- 入口策略: 同一域名，不同路径
  - `/` -> `web`
  - `/app` -> `app`
  - `/admin` -> `admin`

## 1. 先建立正确的部署心智模型

你现在要构建的不是“代码上传到服务器”这么简单，而是下面这条链路：

1. 本地代码进入 GitHub
2. GitHub Actions 执行 CI
3. CI 通过后构建 Docker 镜像
4. 镜像推送到镜像仓库
5. GitHub Actions 通过 SSH 登录到 Swarm manager
6. manager 执行 `docker stack deploy`
7. Swarm 按约束把服务分发到 manager / worker

这一整条链里，GitHub Actions 不直接运行你的服务。
GitHub Actions 只做三件事：验证、打包、触发远端部署。

## 2. 这一套里每个部分分别负责什么

### GitHub CI

CI 只负责确认代码“能不能进入可发布状态”。

它至少要验证三类内容：

- Java 微服务可以编译，必要时跑部分测试
- `oj-agent` 可以安装依赖并跑测试
- `frontend` 三套站点可以测试并构建

如果 CI 失败，就说明这一版代码不应该进入部署流程。

### Docker 镜像

镜像是“可部署产物”。

你不能让服务器每次部署都重新 `git pull` 再本地现编现跑。更稳的做法是：

- GitHub Actions 统一构建镜像
- 推到统一仓库
- 服务器只负责拉镜像和更新服务

这样回滚也简单，因为你回滚的不是代码目录，而是镜像 tag。

### Docker Swarm

Swarm 负责“在哪台机器上跑哪个服务”。

你现在的推荐分工是：

- manager: `nginx`, `web`, `app`, `admin`, `oj-gateway`, `oj-system`, `oj-friend`, `oj-job`
- worker: `oj-agent`, `oj-judge`

原因是：

- manager 同时承担控制面和公网入口，更适合主业务和边缘层
- worker 更适合放 `oj-agent` 和 `oj-judge` 这种相对独立、后续可能需要调资源限制的服务

### Nginx

Nginx 是公网入口，统一接收用户请求，然后按路径转发：

- `/` 转发到 `web`
- `/app` 转发到 `app`
- `/admin` 转发到 `admin`
- API 和 WebSocket 后续通常转发到 `oj-gateway`

### Nacos

Nacos 是运行期业务配置中心，不是 GitHub CI 的替代品。

建议边界如下：

- GitHub Secrets / Swarm env:
  - 镜像仓库用户名密码
  - SSH 私钥
  - 部署目标机器
  - 镜像 tag
- Nacos:
  - MySQL / Redis / RabbitMQ / OSS / ES / Qdrant / agent 运行配置
  - Java 微服务业务配置

## 3. 部署目录里的文件分别是什么

这一批生产部署文件会集中放在 `deploy/prod/`。

你可以先把它理解成三层：

- `env/`
  - 放环境变量样例
- `nginx/`
  - 放统一入口反向代理配置
- `swarm/`
  - 放 `stack.yml` 和部署脚本

## 4. GitHub 里最终需要配置哪些 Secrets

后续做 `cd.yml` 时，至少会需要这些 Secrets：

- `REGISTRY_USERNAME`
- `REGISTRY_PASSWORD`
- `DEPLOY_SSH_HOST`
- `DEPLOY_SSH_USER`
- `DEPLOY_SSH_KEY`
- `STACK_ENV_PROD`
- `RUNTIME_ENV_PROD`

其中：

- `STACK_ENV_PROD` 可以是一整份 `.env` 内容
- `RUNTIME_ENV_PROD` 也是一整份 `.env` 内容，CD 会把它落成服务器上的 `deploy/prod/env/runtime.env`
- 或者拆成多个独立 secret，但前者更适合第一次上线

推荐直接参考：

- `deploy/prod/env/github-secrets-guide.md`
- `deploy/prod/env/stack.env.prod.template`
- `deploy/prod/env/runtime.env.prod.template`

## 4.1 第四课里 CD 具体会做什么

这一版 `cd.yml` 的职责会固定成 4 步：

1. 在 GitHub runner 上构建并推送镜像到 GHCR
2. 通过 SSH 把 `deploy/prod/` 同步到 manager
3. 把 `STACK_ENV_PROD` 和 `RUNTIME_ENV_PROD` 落成服务器文件
4. 在 manager 上执行 `deploy/prod/scripts/deploy.sh`

也就是说，CD 不直接修改远端业务代码目录，而是：

- 推镜像
- 同步部署骨架
- 触发 `docker stack deploy`

这才是更接近生产的方式。

## 5. 第一次上线的推荐顺序

不要一上来就写完整 CD。正确顺序是：

1. 先补 Dockerfile
2. 再补 `stack.yml`
3. 先在服务器手工跑一次 `docker stack deploy`
4. 手工部署跑通后，再写 GitHub CD

这是因为：

- 如果手工 deploy 都没跑通，GitHub CD 只会把问题藏得更深
- 先打通手工链路，再做自动化，排错效率最高

## 6. 你现在最该记住的一句话

GitHub Actions 不是运行环境，Swarm 才是运行环境。

GitHub Actions 负责把“代码”变成“镜像”，再通知 Swarm 更新服务。
