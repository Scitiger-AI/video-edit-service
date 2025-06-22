from celery import Celery
from .config import settings

# 创建Celery实例
celery_app = Celery(
    settings.APP_NAME,
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# 配置Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.TASK_TIME_LIMIT,
    worker_prefetch_multiplier=1,  # 每次只获取一个任务
    worker_max_tasks_per_child=200,  # 处理200个任务后重启工作进程
    mongodb_backend_settings={
        'database': settings.MONGODB_DB_NAME,
        'taskmeta_collection': 'celery_tasks',
    },
    # 设置默认队列名称，基于服务名称确保唯一性
    task_default_queue=f"{settings.SERVICE_NAME}_queue",
    # 定义队列
    task_queues={
        f"{settings.SERVICE_NAME}_queue": {
            "exchange": f"{settings.SERVICE_NAME}_exchange",
            "routing_key": f"{settings.SERVICE_NAME}_key",
        }
    },
    # 设置默认交换机和路由键
    task_default_exchange=f"{settings.SERVICE_NAME}_exchange",
    task_default_routing_key=f"{settings.SERVICE_NAME}_key",
)

# 自动发现任务
celery_app.autodiscover_tasks(["app.worker"]) 