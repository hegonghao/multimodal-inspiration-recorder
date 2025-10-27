"""
Security Module
安全认证和授权模块
"""

import secrets
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
import hashlib
import hmac

from src.config import settings
from src.models.user import User, UserCreate
from src.utils.logger import get_logger
from src.utils.metrics import track_request, track_error

logger = get_logger(__name__)


class SecurityError(Exception):
    """安全相关异常基类"""
    pass


class AuthenticationError(SecurityError):
    """认证失败异常"""
    pass


class AuthorizationError(SecurityError):
    """授权失败异常"""
    pass


class TokenError(SecurityError):
    """令牌错误异常"""
    pass


class PasswordManager:
    """密码管理器"""

    def __init__(self):
        self.pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=12
        )

    def hash_password(self, password: str) -> str:
        """哈希密码"""
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return self.pwd_context.verify(plain_password, hashed_password)

    def generate_password_reset_token(self, length: int = 32) -> str:
        """生成密码重置令牌"""
        return secrets.token_urlsafe(length)

    def validate_password_strength(self, password: str) -> Dict[str, Any]:
        """验证密码强度"""
        result = {
            "valid": True,
            "score": 0,
            "issues": []
        }

        # 长度检查
        if len(password) < 8:
            result["valid"] = False
            result["issues"].append("密码长度至少8位")
        elif len(password) >= 12:
            result["score"] += 2
        else:
            result["score"] += 1

        # 复杂度检查
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

        complexity_score = sum([has_upper, has_lower, has_digit, has_special])
        result["score"] += complexity_score

        if complexity_score < 2:
            result["valid"] = False
            result["issues"].append("密码必须包含大小写字母、数字或特殊字符中的至少2种")

        # 常见密码检查
        common_passwords = [
            "password", "123456", "123456789", "qwerty", "abc123",
            "password123", "admin", "root", "user", "test"
        ]

        if password.lower() in common_passwords:
            result["valid"] = False
            result["issues"].append("密码过于常见，请使用更安全的密码")
            result["score"] = 0

        return result


class TokenManager:
    """JWT 令牌管理器"""

    def __init__(self):
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.ALGORITHM
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES

    def create_access_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """创建访问令牌"""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=self.access_token_expire_minutes
            )

        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        })

        try:
            encoded_jwt = jwt.encode(
                to_encode,
                self.secret_key,
                algorithm=self.algorithm
            )
            return encoded_jwt
        except Exception as e:
            logger.error(f"Token creation failed: {e}")
            raise TokenError("令牌创建失败")

    def verify_token(self, token: str) -> Dict[str, Any]:
        """验证令牌"""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        except JWTError as e:
            logger.warning(f"Token verification failed: {e}")
            raise TokenError("令牌无效或已过期")
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            raise TokenError("令牌验证失败")

    def create_refresh_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """创建刷新令牌"""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=7)  # 刷新令牌7天有效

        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        })

        try:
            encoded_jwt = jwt.encode(
                to_encode,
                self.secret_key,
                algorithm=self.algorithm
            )
            return encoded_jwt
        except Exception as e:
            logger.error(f"Refresh token creation failed: {e}")
            raise TokenError("刷新令牌创建失败")

    def extract_token_from_header(self, authorization: str) -> str:
        """从 Authorization 头中提取令牌"""
        if not authorization:
            raise AuthenticationError("缺少 Authorization 头")

        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise AuthenticationError("Authorization 头格式错误")

        return parts[1]


class APIKeyManager:
    """API 密钥管理器"""

    def __init__(self):
        self.api_keys: Dict[str, Dict[str, Any]] = {}
        self.key_prefix = "mr_"  # MultiModal Recorder

    def generate_api_key(self, user_id: str, name: str) -> str:
        """生成 API 密钥"""
        # 生成随机密钥
        random_part = secrets.token_urlsafe(32)
        api_key = f"{self.key_prefix}{random_part}"

        # 存储密钥信息
        self.api_keys[api_key] = {
            "user_id": user_id,
            "name": name,
            "created_at": datetime.utcnow(),
            "last_used": None,
            "usage_count": 0,
            "is_active": True
        }

        logger.info(f"Generated API key for user {user_id}")
        return api_key

    def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """验证 API 密钥"""
        if api_key not in self.api_keys:
            return None

        key_info = self.api_keys[api_key]
        if not key_info["is_active"]:
            return None

        # 更新使用信息
        key_info["last_used"] = datetime.utcnow()
        key_info["usage_count"] += 1

        return key_info

    def revoke_api_key(self, api_key: str) -> bool:
        """撤销 API 密钥"""
        if api_key in self.api_keys:
            self.api_keys[api_key]["is_active"] = False
            logger.info(f"Revoked API key: {api_key[:8]}...")
            return True
        return False

    def list_user_api_keys(self, user_id: str) -> List[Dict[str, Any]]:
        """列出用户的 API 密钥"""
        user_keys = []
        for key, info in self.api_keys.items():
            if info["user_id"] == user_id:
                user_keys.append({
                    "key": key[:8] + "...",  # 只显示前8位
                    "name": info["name"],
                    "created_at": info["created_at"],
                    "last_used": info["last_used"],
                    "usage_count": info["usage_count"],
                    "is_active": info["is_active"]
                })
        return user_keys


class RateLimiter:
    """速率限制器"""

    def __init__(self):
        self.requests: Dict[str, List[float]] = {}

    def is_allowed(
        self,
        identifier: str,
        limit: int,
        window: int
    ) -> Dict[str, Any]:
        """检查是否允许请求"""
        now = time.time()
        window_start = now - window

        # 清理过期记录
        if identifier in self.requests:
            self.requests[identifier] = [
                req_time for req_time in self.requests[identifier]
                if req_time > window_start
            ]
        else:
            self.requests[identifier] = []

        current_count = len(self.requests[identifier])

        if current_count >= limit:
            # 找到最早的请求时间
            oldest_request = min(self.requests[identifier]) if self.requests[identifier] else now
            retry_after = int(oldest_request + window - now)

            return {
                "allowed": False,
                "current": current_count,
                "limit": limit,
                "retry_after": max(retry_after, 1)
            }

        # 记录当前请求
        self.requests[identifier].append(now)

        return {
            "allowed": True,
            "current": current_count + 1,
            "limit": limit,
            "remaining": limit - current_count - 1,
            "reset_time": int(window_start + window)
        }


class SecurityManager:
    """安全管理器"""

    def __init__(self):
        self.password_manager = PasswordManager()
        self.token_manager = TokenManager()
        self.api_key_manager = APIKeyManager()
        self.rate_limiter = RateLimiter()

    @track_request("security.authenticate")
    def authenticate_user(
        self,
        username: str,
        password: str
    ) -> Optional[Dict[str, Any]]:
        """用户认证"""
        # 这里应该从数据库获取用户信息
        # 暂时使用模拟数据
        mock_user = {
            "id": "user_123",
            "username": username,
            "hashed_password": self.password_manager.hash_password("password123"),
            "is_active": True,
            "roles": ["user"]
        }

        if not mock_user or not self.password_manager.verify_password(
            password, mock_user["hashed_password"]
        ):
            track_error("security.authentication_failed", {"username": username})
            raise AuthenticationError("用户名或密码错误")

        if not mock_user["is_active"]:
            raise AuthenticationError("用户账户已被禁用")

        logger.info(f"User authenticated successfully: {username}")
        return mock_user

    def create_user_tokens(self, user: Dict[str, Any]) -> Dict[str, str]:
        """为用户创建令牌"""
        access_token = self.token_manager.create_access_token(
            data={
                "sub": user["id"],
                "username": user["username"],
                "roles": user["roles"]
            }
        )

        refresh_token = self.token_manager.create_refresh_token(
            data={
                "sub": user["id"],
                "username": user["username"]
            }
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }

    def verify_access_token(self, token: str) -> Dict[str, Any]:
        """验证访问令牌"""
        try:
            payload = self.token_manager.verify_token(token)

            if payload.get("type") != "access":
                raise TokenError("令牌类型错误")

            return payload
        except Exception as e:
            logger.warning(f"Access token verification failed: {e}")
            raise AuthenticationError("访问令牌无效")

    def authorize_user(
        self,
        payload: Dict[str, Any],
        required_roles: List[str] = None
    ) -> bool:
        """授权用户"""
        user_roles = payload.get("roles", [])

        if required_roles:
            # 检查用户是否具有所需角色
            if not any(role in user_roles for role in required_roles):
                logger.warning(
                    f"Authorization failed: user roles {user_roles} "
                    f"do not include required roles {required_roles}"
                )
                raise AuthorizationError("权限不足")

        return True

    def create_api_key(self, user_id: str, name: str) -> str:
        """创建 API 密钥"""
        return self.api_key_manager.generate_api_key(user_id, name)

    def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """验证 API 密钥"""
        return self.api_key_manager.validate_api_key(api_key)

    def check_rate_limit(
        self,
        identifier: str,
        limit: int,
        window: int
    ) -> Dict[str, Any]:
        """检查速率限制"""
        result = self.rate_limiter.is_allowed(identifier, limit, window)

        if not result["allowed"]:
            logger.warning(
                f"Rate limit exceeded for {identifier}: "
                f"{result['current']}/{result['limit']}"
            )

        return result

    def generate_csrf_token(self) -> str:
        """生成 CSRF 令牌"""
        return secrets.token_urlsafe(32)

    def verify_csrf_token(self, token: str, expected_token: str) -> bool:
        """验证 CSRF 令牌"""
        return hmac.compare_digest(token, expected_token)

    def hash_data(self, data: str) -> str:
        """哈希数据"""
        return hashlib.sha256(data.encode()).hexdigest()

    def verify_data_hash(self, data: str, expected_hash: str) -> bool:
        """验证数据哈希"""
        return hmac.compare_digest(
            self.hash_data(data),
            expected_hash
        )


# 全局安全管理器实例
security_manager = SecurityManager()


# 依赖注入函数
async def get_current_user(token: str) -> Dict[str, Any]:
    """获取当前用户"""
    try:
        payload = security_manager.verify_access_token(token)
        user_id = payload.get("sub")

        if user_id is None:
            raise AuthenticationError("令牌中缺少用户信息")

        # 这里应该从数据库获取完整用户信息
        user = {
            "id": user_id,
            "username": payload.get("username"),
            "roles": payload.get("roles", [])
        }

        return user

    except Exception as e:
        logger.error(f"Get current user failed: {e}")
        raise AuthenticationError("获取用户信息失败")


async def get_current_active_user(current_user: Dict[str, Any]) -> Dict[str, Any]:
    """获取当前活跃用户"""
    # 检查用户是否活跃
    if not current_user.get("is_active", True):
        raise AuthenticationError("用户账户已被禁用")

    return current_user


def require_roles(required_roles: List[str]):
    """角色要求装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 这里需要从请求中获取用户信息
            # 实际实现中需要根据具体框架调整
            user = kwargs.get("current_user")
            if not user:
                raise AuthenticationError("未找到用户信息")

            if not security_manager.authorize_user(user, required_roles):
                raise AuthorizationError("权限不足")

            return await func(*args, **kwargs)
        return wrapper
    return decorator