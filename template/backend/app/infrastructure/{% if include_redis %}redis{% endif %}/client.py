from redis.asyncio import BlockingConnectionPool, Redis
from redis.asyncio.retry import Retry
from redis.backoff import EqualJitterBackoff
from redis.exceptions import ConnectionError as RedisConnectionError

from app.infrastructure.redis.log_events import RedisClosed, RedisInitialized
from app.shared import logging as log

logger = log.get_logger(__name__)

REDIS_MAXIMUM_CONNECTIONS = 50
REDIS_POOL_TIMEOUT_SECONDS = 2.0
REDIS_SOCKET_TIMEOUT_SECONDS = 5.0
REDIS_HEALTH_CHECK_INTERVAL_SECONDS = 30
REDIS_RETRY_ATTEMPTS = 3


class RedisClient:
    def __init__(self, dsn: str, *, client_name: str) -> None:
        pool = BlockingConnectionPool.from_url(
            dsn,
            max_connections=REDIS_MAXIMUM_CONNECTIONS,
            timeout=REDIS_POOL_TIMEOUT_SECONDS,
            socket_timeout=REDIS_SOCKET_TIMEOUT_SECONDS,
            socket_connect_timeout=REDIS_SOCKET_TIMEOUT_SECONDS,
            socket_keepalive=True,
            health_check_interval=REDIS_HEALTH_CHECK_INTERVAL_SECONDS,
            retry=Retry(
                EqualJitterBackoff(base=0.05, cap=1.0),
                REDIS_RETRY_ATTEMPTS,
                supported_errors=(RedisConnectionError,),
            ),
            decode_responses=False,
            protocol=3,
            client_name=client_name,
        )
        self.client = Redis.from_pool(pool)

    async def initialize(self) -> None:
        await self.client.ping()
        log.emit(logger, event=RedisInitialized())

    async def close(self) -> None:
        await self.client.aclose()
        log.emit(logger, event=RedisClosed())
