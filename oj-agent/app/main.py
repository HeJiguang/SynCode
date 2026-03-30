from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.chat import router as chat_router
from app.api.training import router as training_router
from app.core.config import load_settings
from app.core.nacos_registry import NacosRegistry
from app.retrieval.routes.dense import bootstrap_dense_index


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # 【启动阶段：准备工作】
    settings = load_settings()
    registry = NacosRegistry(settings) 
    
    # 尝试将当前服务注册到 Nacos 注册中心
    try:
        registry.register()
    except Exception:
        # Keep oj-agent runnable even when Nacos is absent.
        pass

    # 尝试初始化向量密集索引（Dense Index）
    try:
        bootstrap_dense_index()
    except Exception:
        # Keep oj-agent runnable even when dense indexing is unavailable.
        pass

    # 【运行阶段】
    try:
        yield  # 此时应用正式启动并开始处理 HTTP 请求
        
    # 【关闭阶段：清理工作】
    finally:
        try:
            # 应用关闭时，从 Nacos 注销该服务
            registry.deregister()
        except Exception:
            pass



app = FastAPI(title="OJ Agent", version="0.1.0", lifespan=lifespan)
app.include_router(chat_router)
app.include_router(training_router)
