# Local Pressure Test Setup

This directory is for the local test mode where Java services read `application-local.yml`
directly and do not use Nacos by default.

Current intended topology:

- MySQL: can stay on cloud or local
- Redis: local
- RabbitMQ: local
- Elasticsearch: local
- `oj-agent`: local
- Java services: local
- Nacos: disabled by default for local profile

Recommended startup order:

1. Create your own `local-env.ps1` from `local-env.example.ps1`, then load it into your current PowerShell session.
   - `local-env.ps1` is intentionally local-only and should not be committed.
2. Use `start-local-stack.ps1` for the full local stack.
3. Run `status-local-stack.ps1` or `check-local-services.ps1`.
4. Use `stop-local-stack.ps1` when you want to stop all local processes started by the helper.

One-command startup:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\deploy\dev\local\start-local-stack.ps1
```

This script will:

- load `local-env.ps1`
- run `mvn -q -Dmaven.repo.local=temp/m2-repo -DskipTests install`
- start `oj-agent`
- start `oj-system`, `oj-judge`, `oj-friend`, `oj-gateway`, `oj-job`
- start frontend `web`, `app`, `admin`
- wait for backend and frontend HTTP checks to pass
- write pid files and logs to `logs/local-runtime/`

Current local frontend defaults from `local-env.ps1`:

- `web`: `http://127.0.0.1:4000`
- `app`: `http://127.0.0.1:4201/app`
- `admin`: `http://127.0.0.1:4002/admin`

The frontend ports are configurable through `FRONTEND_WEB_PORT`, `FRONTEND_APP_PORT`,
and `FRONTEND_ADMIN_PORT`. The local app default uses `4201` to avoid a common
Windows port conflict on `4001`.

Useful commands:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\deploy\dev\local\status-local-stack.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\deploy\dev\local\stop-local-stack.ps1
```

Optional flags:

- `-SkipMavenInstall`: skip the snapshot install step
- `-SkipJob`: do not start `oj-job`
- `-SkipFrontends`: only start backend services and agent

Example commands:

```powershell
. .\deploy\dev\local\local-env.ps1

mvn -q -Dmaven.repo.local=temp/m2-repo -DskipTests install

mvn -f oj-modules/oj-system/pom.xml -Dmaven.repo.local=temp/m2-repo spring-boot:run "-Dspring-boot.run.profiles=local"
mvn -f oj-modules/oj-judge/pom.xml -Dmaven.repo.local=temp/m2-repo spring-boot:run "-Dspring-boot.run.profiles=local"
mvn -f oj-modules/oj-friend/pom.xml -Dmaven.repo.local=temp/m2-repo spring-boot:run "-Dspring-boot.run.profiles=local"
mvn -f oj-gateway/pom.xml -Dmaven.repo.local=temp/m2-repo spring-boot:run "-Dspring-boot.run.profiles=local"
```

Notes:

- Local mode keeps Nacos off unless you explicitly export `NACOS_ENABLED=true`.
- `oj-friend` calls `oj-judge` through Spring simple discovery in local mode, so
  `OJ_JUDGE_BASE_URL` must match the actual local judge address.
- `oj-gateway` routes to local `oj-friend` and `oj-agent`, so `OJ_FRIEND_BASE_URL`
  and `AI_GATEWAY_URI` must match the actual addresses.
- `local-env.ps1` is wired for the current local-test setup: cloud MySQL plus
  local Redis, RabbitMQ, Elasticsearch, and local application services.
- The checked-in template `local-env.example.ps1` uses agent port `8016` to avoid
  a common dirty local listener on `8015`.
- `oj-job` can start locally, but its registration to `xxl-job-admin` may still depend
  on the admin-side access token configuration.
- Local login / mail testing uses `MAIL_IS_SEND=false` by default, so email codes are
  not sent to a real mailbox in local mode. The code path still works, but the local
  default verification code is `123456`.
