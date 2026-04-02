from dataclasses import dataclass
import logging
import os
from typing import Any

import httpx
import yaml


# 初始化当前模块的日志记录器
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class NacosBootstrap:
    """
    Nacos 启动引导配置类 (NacosBootstrap)
    
    专门用于存储连接 Nacos 服务器所需的元数据（元配置）。
    使用 frozen=True 确保这些基础连接信息在初始化后不可被篡改。
    """
    enabled: bool                # 是否启用了 Nacos 配置拉取
    server_addr: str | None      # Nacos 服务器地址 (例如: http://127.0.0.1:8848)
    namespace: str | None        # 命名空间 ID (Tenant)，用于隔离不同环境 (如 dev, prod)
    group: str                   # 配置分组，默认通常是 DEFAULT_GROUP
    data_id: str                 # 配置文件 ID (类似于文件名，如 oj-agent-local.yaml)
    username: str | None         # Nacos 控制台用户名（开启鉴权时需要）
    password: str | None         # Nacos 控制台密码


NACOS_HTTP_TIMEOUT_SECONDS = 10.0


def _to_bool(raw: str | None, default: bool) -> bool:
    """内部辅助函数：安全地将环境变量字符串解析为布尔值"""
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _bootstrap() -> NacosBootstrap:
    """
    从系统环境变量中提取 Nacos 的连接信息，构造引导配置对象。
    注意：在拉取远程配置之前，系统必须先知道去哪里拉取，所以这些信息只能硬编码或放在环境变量里。
    """
    server_addr = os.getenv("OJ_AGENT_NACOS_SERVER_ADDR")
    return NacosBootstrap(
        # 如果配置了 server_addr，就默认开启 Nacos 拉取，除非明确设置了不开启
        enabled=_to_bool(os.getenv("OJ_AGENT_NACOS_CONFIG_ENABLED"), bool(server_addr)),
        server_addr=server_addr,
        namespace=os.getenv("OJ_AGENT_NACOS_NAMESPACE"),
        group=os.getenv("OJ_AGENT_NACOS_GROUP", "DEFAULT_GROUP"),
        data_id=os.getenv("OJ_AGENT_NACOS_CONFIG_DATA_ID", "oj-agent-local.yaml"),
        username=os.getenv("OJ_AGENT_NACOS_USERNAME"),
        password=os.getenv("OJ_AGENT_NACOS_PASSWORD"),
    )


def _login(client: httpx.Client, bootstrap: NacosBootstrap) -> str | None:
    """
    Nacos 鉴权登录逻辑。
    
    如果配置了账号密码，向 Nacos 的 Auth 接口发起 POST 请求获取 Token。
    """
    if not bootstrap.username or not bootstrap.password:
        return None  # 未配置账号密码则跳过登录，适用于未开启鉴权的 Nacos 集群
        
    # 发起登录请求。rstrip("/") 是为了防止 URL 拼接时出现双斜杠 (//)
    response = client.post(
        bootstrap.server_addr.rstrip("/") + "/nacos/v1/auth/users/login",
        data={
            "username": bootstrap.username,
            "password": bootstrap.password,
        },
    )
    # 核心细节：如果登录失败（如密码错误、403、500），直接抛出异常，阻断后续流程
    response.raise_for_status()
    payload = response.json()
    # 返回鉴权 Token (accessToken)
    return payload.get("accessToken")


def _query_params(bootstrap: NacosBootstrap, access_token: str | None) -> dict[str, str]:
    """
    构造拉取配置时所需的 HTTP GET 查询参数 (Query Parameters)。
    """
    params = {
        "dataId": bootstrap.data_id,
        "group": bootstrap.group,
    }
    # Nacos 的命名空间在 API 参数里通常叫 tenant
    if bootstrap.namespace:
        params["tenant"] = bootstrap.namespace
    # 如果有 Token，带上它以通过接口鉴权
    if access_token:
        params["accessToken"] = access_token
    return params


def load_nacos_config() -> dict[str, Any]:
    """
    主入口函数：加载并解析 Nacos 远程配置。
    
    返回一个包含原始文本 ("raw") 和解析后字典 ("data") 的结构。
    如果出现任何网络或解析错误，会安全地返回空字典，绝不导致主程序崩溃。
    """
    bootstrap = _bootstrap()
    # 如果未开启，或者根本没配置服务器地址，直接返回空，走本地配置逻辑
    if not bootstrap.enabled or not bootstrap.server_addr:
        return {}

    try:
        # 使用 httpx 作为 HTTP 客户端（比 requests 更现代，性能更好）。
        # 设置 timeout=5.0 极其重要：防止 Nacos 服务器无响应时，导致整个应用在启动时无限期挂死 (Hang)。
        with httpx.Client(timeout=NACOS_HTTP_TIMEOUT_SECONDS, trust_env=False) as client:
            # 1. 尝试登录获取 Token
            access_token = _login(client, bootstrap)
            
            # 2. 拉取具体的配置文件
            response = client.get(
                bootstrap.server_addr.rstrip("/") + "/nacos/v1/cs/configs",
                params=_query_params(bootstrap, access_token),
            )
            response.raise_for_status()
            # 获取原始配置文本（通常是 YAML 或 JSON 格式的字符串）
            raw = response.text
            
        # 3. 解析 YAML 数据
        # safe_load 会避免执行 YAML 中可能嵌入的恶意 Python 函数
        data = yaml.safe_load(raw) or {}
        
        # 4. 防御性检查：确保解析出来的是字典格式
        if not isinstance(data, dict):
            return {"raw": raw, "data": {}}
            
        return {"raw": raw, "data": data}
        
    except Exception as exc:
        # 容错/降级核心：捕获所有异常（网络超时、鉴权失败、YAML 解析错误等）。
        # 仅打印警告日志，返回空字典。外层代码（如 config.py）接收到空字典后，会自动退化使用本地的 .env 文件或默认值。
        LOGGER.warning("Failed to load oj-agent config from Nacos.", exc_info=exc)
        return {}
