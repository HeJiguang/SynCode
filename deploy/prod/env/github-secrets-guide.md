# GitHub Secrets Preparation Guide

这份文档只回答一个问题：
GitHub 仓库里的 7 个 Secrets，分别应该填什么。

## 1. 需要创建的 Secrets

### `REGISTRY_USERNAME`

作用：
用于登录 GHCR。

建议值：

- 如果镜像推到当前 GitHub 账号名下，直接填你的 GitHub 用户名
- 如果镜像推到 GitHub 组织名下，填具备包发布权限的账号名

### `REGISTRY_PASSWORD`

作用：
用于登录 GHCR。

建议值：

- 一个 GitHub Personal Access Token
- 至少要具备 `write:packages`
- 如果仓库是私有的，通常也需要 `repo`

### `DEPLOY_SSH_HOST`

作用：
CD 登录到哪台服务器执行部署。

当前真实值：

```env
101.96.200.76
```

也就是 Swarm manager。

### `DEPLOY_SSH_USER`

作用：
SSH 登录用户名。

建议值：

- 你服务器上实际用于部署的用户
- 常见是 `root`，但更推荐专门部署用户

### `DEPLOY_SSH_KEY`

作用：
CD 用它通过 SSH 登录 manager。

填写内容：

- 对应 `DEPLOY_SSH_USER` 的私钥全文
- 一般是 `id_ed25519` 的完整内容
- 必须包含开头和结尾行

示例格式：

```text
-----BEGIN OPENSSH PRIVATE KEY-----
...
-----END OPENSSH PRIVATE KEY-----
```

### `STACK_ENV_PROD`

作用：
决定 stack 级别的镜像名、域名、节点约束。

填写方式：

- 直接把 `deploy/prod/env/stack.env.prod.template` 的内容复制进去
- 其中 `ghcr.io/your-org-or-user` 可以保留不改，CD 会自动替换成当前仓库 owner 的 GHCR 命名空间
- `sha-REPLACE_ME` 也不需要手改，CD 会自动替换成本次发布 tag

### `RUNTIME_ENV_PROD`

作用：
决定运行期环境变量。

填写方式：

- 直接把 `deploy/prod/env/runtime.env.prod.template` 的内容复制进去
- 把里面的占位项替换成真实 prod 值
- 能放到 Nacos 的业务配置仍建议继续放 Nacos，这里更适合“服务启动必须知道”的连接信息

## 2. 建议填写顺序

1. 先填 `DEPLOY_SSH_HOST`
2. 再填 `DEPLOY_SSH_USER`
3. 再填 `DEPLOY_SSH_KEY`
4. 再填 `REGISTRY_USERNAME`
5. 再填 `REGISTRY_PASSWORD`
6. 最后填 `STACK_ENV_PROD`
7. 最后填 `RUNTIME_ENV_PROD`

这样最好排错。

原因：

- SSH 不通，后面 secrets 都白填
- Registry 登不上，镜像推不出去
- env 文件不对，部署能触发但服务起不来

## 3. 第一次填写后最该检查什么

### SSH 侧

- manager 上能否用对应用户执行 `docker stack deploy`
- 该用户是否已加入 `docker` 组，或本身就是 `root`
- `~/onlineoj` 路径是否允许写入

### Registry 侧

- GHCR 中能否创建包
- PAT 是否真的有 `write:packages`

### Env 侧

- `PUBLIC_DOMAIN` 是否已经解析到入口服务器
- `NACOS_NAMESPACE` 是否是 prod namespace，不是 dev
- `AGENT_PUBLIC_BASE_URL` 是否和实际对外访问方式一致

## 4. 一个很实用的判断标准

如果某个值是：

- 部署流程自己生成的，例如镜像 tag
  - 不要手填死
- 服务启动时必须拿到的，例如 Nacos / MySQL / Redis 地址
  - 放 `RUNTIME_ENV_PROD`
- stack 编排时必须知道的，例如镜像名、节点约束、域名
  - 放 `STACK_ENV_PROD`
