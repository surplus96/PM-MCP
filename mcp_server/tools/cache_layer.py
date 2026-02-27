"""캐싱 레이어 - Phase 3 Week 4

Redis 기반 캐싱으로 팩터 분석 성능 최적화
"""

import json
import hashlib
import logging
from typing import Any, Optional, Dict, Callable
from datetime import datetime, timedelta
from functools import wraps

logger = logging.getLogger(__name__)


class CacheLayer:
    """Redis 기반 캐싱 레이어"""

    def __init__(self, redis_url: Optional[str] = None, enabled: bool = True):
        """캐시 레이어 초기화

        Args:
            redis_url: Redis 연결 URL (default: redis://localhost:6379/0)
            enabled: 캐싱 활성화 여부
        """
        self.enabled = enabled
        self.redis_client = None

        if not self.enabled:
            logger.info("Caching is disabled")
            return

        try:
            import redis
            self.redis_url = redis_url or "redis://localhost:6379/0"
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            # 연결 테스트
            self.redis_client.ping()
            logger.info(f"Redis cache connected: {self.redis_url}")
        except ImportError:
            logger.warning("redis package not installed, caching disabled")
            self.enabled = False
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}, caching disabled")
            self.enabled = False

    def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 가져오기

        Args:
            key: 캐시 키

        Returns:
            캐시된 값 (없으면 None)
        """
        if not self.enabled or not self.redis_client:
            return None

        try:
            value = self.redis_client.get(key)
            if value:
                logger.debug(f"Cache hit: {key}")
                return json.loads(value)
            else:
                logger.debug(f"Cache miss: {key}")
                return None
        except Exception as e:
            logger.warning(f"Cache get failed for {key}: {e}")
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """캐시에 값 저장

        Args:
            key: 캐시 키
            value: 저장할 값
            ttl: TTL (초 단위, None이면 영구)

        Returns:
            성공 여부
        """
        if not self.enabled or not self.redis_client:
            return False

        try:
            serialized = json.dumps(value, default=str)
            if ttl:
                self.redis_client.setex(key, ttl, serialized)
            else:
                self.redis_client.set(key, serialized)
            logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.warning(f"Cache set failed for {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """캐시에서 값 삭제

        Args:
            key: 캐시 키

        Returns:
            성공 여부
        """
        if not self.enabled or not self.redis_client:
            return False

        try:
            self.redis_client.delete(key)
            logger.debug(f"Cache deleted: {key}")
            return True
        except Exception as e:
            logger.warning(f"Cache delete failed for {key}: {e}")
            return False

    def clear_pattern(self, pattern: str) -> int:
        """패턴에 맞는 캐시 일괄 삭제

        Args:
            pattern: 키 패턴 (예: "factor:*")

        Returns:
            삭제된 키 개수
        """
        if not self.enabled or not self.redis_client:
            return 0

        try:
            keys = list(self.redis_client.scan_iter(match=pattern))
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(f"Cache cleared: {deleted} keys matching '{pattern}'")
                return deleted
            return 0
        except Exception as e:
            logger.warning(f"Cache clear failed for pattern {pattern}: {e}")
            return 0

    @staticmethod
    def generate_key(prefix: str, **kwargs) -> str:
        """캐시 키 생성

        Args:
            prefix: 키 prefix
            **kwargs: 키 구성 요소

        Returns:
            캐시 키
        """
        # 정렬된 키-값으로 일관성 보장
        sorted_items = sorted(kwargs.items())
        components = [f"{k}={v}" for k, v in sorted_items]
        key_string = ":".join([prefix] + components)

        # 길이가 너무 길면 해시 사용
        if len(key_string) > 200:
            hash_suffix = hashlib.md5(key_string.encode()).hexdigest()[:12]
            key_string = f"{prefix}:hash:{hash_suffix}"

        return key_string

    def cached(
        self,
        prefix: str,
        ttl: int = 3600,
        key_func: Optional[Callable] = None
    ):
        """함수 결과 캐싱 데코레이터

        Args:
            prefix: 캐시 키 prefix
            ttl: TTL (초 단위)
            key_func: 커스텀 키 생성 함수

        Usage:
            @cache.cached(prefix="financial_factors", ttl=1800)
            def get_financial_factors(ticker, market):
                # ...expensive operation...
                return result
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # 캐싱 비활성화 시 바로 실행
                if not self.enabled:
                    return func(*args, **kwargs)

                # 캐시 키 생성
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    # 기본 키: prefix:arg1:arg2:kwarg1=val1:kwarg2=val2
                    key_parts = [prefix]
                    key_parts.extend([str(arg) for arg in args])
                    key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
                    cache_key = ":".join(key_parts)

                # 캐시 확인
                cached_value = self.get(cache_key)
                if cached_value is not None:
                    return cached_value

                # 캐시 미스: 함수 실행
                result = func(*args, **kwargs)

                # 결과 캐싱
                self.set(cache_key, result, ttl)

                return result

            return wrapper
        return decorator

    def get_stats(self) -> Dict:
        """캐시 통계 조회

        Returns:
            캐시 통계 정보
        """
        if not self.enabled or not self.redis_client:
            return {
                'enabled': False,
                'status': 'disabled'
            }

        try:
            info = self.redis_client.info('stats')
            return {
                'enabled': True,
                'status': 'connected',
                'total_keys': self.redis_client.dbsize(),
                'hits': info.get('keyspace_hits', 0),
                'misses': info.get('keyspace_misses', 0),
                'hit_rate': self._calculate_hit_rate(
                    info.get('keyspace_hits', 0),
                    info.get('keyspace_misses', 0)
                )
            }
        except Exception as e:
            logger.warning(f"Failed to get cache stats: {e}")
            return {
                'enabled': True,
                'status': 'error',
                'error': str(e)
            }

    @staticmethod
    def _calculate_hit_rate(hits: int, misses: int) -> float:
        """캐시 히트율 계산"""
        total = hits + misses
        if total == 0:
            return 0.0
        return round((hits / total) * 100, 2)


# 전역 캐시 인스턴스
_global_cache: Optional[CacheLayer] = None


def get_cache(redis_url: Optional[str] = None, enabled: bool = True) -> CacheLayer:
    """전역 캐시 인스턴스 가져오기

    Args:
        redis_url: Redis URL
        enabled: 캐싱 활성화 여부

    Returns:
        CacheLayer 인스턴스
    """
    global _global_cache

    if _global_cache is None:
        _global_cache = CacheLayer(redis_url=redis_url, enabled=enabled)

    return _global_cache


# TTL 상수 (초 단위)
class CacheTTL:
    """캐시 TTL 상수"""
    FINANCIAL_FACTORS = 3600  # 1시간 (재무 데이터는 자주 변하지 않음)
    TECHNICAL_INDICATORS = 300  # 5분 (기술적 지표는 시장 시간 동안 자주 변함)
    SENTIMENT_ANALYSIS = 1800  # 30분 (감성 분석은 중간 정도)
    NEWS_ARTICLES = 600  # 10분 (뉴스는 자주 업데이트됨)
    BACKTEST_RESULTS = 86400  # 24시간 (백테스트는 하루에 한 번 정도 변경)
    THEME_ANALYSIS = 1800  # 30분 (테마 분석 종합 결과)
