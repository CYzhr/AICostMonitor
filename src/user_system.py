#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户系统模块
多用户注册、认证、配额管理
支持付费用户功能
"""

import hashlib
import secrets
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import sqlite3
import logging

logger = logging.getLogger(__name__)


@dataclass
class User:
    """用户信息"""
    user_id: str
    email: str
    username: str
    created_at: str
    last_login: str
    account_type: str  # free, pro, enterprise
    api_key: str
    monthly_budget: float
    monthly_used: float
    api_quota: Dict[str, int]  # 各API提供商的配额
    is_active: bool
    billing_info: Optional[Dict[str, Any]] = None


@dataclass
class APIUsage:
    """API使用记录"""
    usage_id: str
    user_id: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    timestamp: str
    request_id: Optional[str] = None


class UserManager:
    """用户管理器"""
    
    def __init__(self, db_path: str = "/root/.openclaw/workspace/data/users.db"):
        """
        初始化用户管理器
        
        Args:
            db_path: 数据库路径
        """
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 用户表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            last_login TEXT,
            account_type TEXT NOT NULL,
            api_key TEXT UNIQUE NOT NULL,
            monthly_budget REAL DEFAULT 100.0,
            monthly_used REAL DEFAULT 0.0,
            api_quota TEXT,  -- JSON格式
            is_active INTEGER DEFAULT 1,
            billing_info TEXT  -- JSON格式
        )
        ''')
        
        # API使用记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_usage (
            usage_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            input_tokens INTEGER NOT NULL,
            output_tokens INTEGER NOT NULL,
            cost REAL NOT NULL,
            timestamp TEXT NOT NULL,
            request_id TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON api_usage (user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON api_usage (timestamp)')
        
        conn.commit()
        conn.close()
        
        # 创建默认管理员用户（如果不存在）
        if self._is_database_empty():
            self._create_default_users()
    
    def _is_database_empty(self) -> bool:
        """检查数据库是否为空"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        conn.close()
        return count == 0
    
    def _create_default_users(self):
        """创建默认用户"""
        # 默认免费用户
        self.register_user(
            email="demo@example.com",
            username="demo_user",
            password="demo123",
            account_type="free"
        )
        
        # 测试专业用户
        self.register_user(
            email="test@example.com", 
            username="test_pro",
            password="test123",
            account_type="pro"
        )
        
        logger.info("创建了默认测试用户")
    
    def _hash_password(self, password: str) -> str:
        """哈希密码"""
        salt = secrets.token_hex(16)
        return f"{salt}${hashlib.sha256((salt + password).encode()).hexdigest()}"
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """验证密码"""
        try:
            salt, expected_hash = password_hash.split('$')
            actual_hash = hashlib.sha256((salt + password).encode()).hexdigest()
            return actual_hash == expected_hash
        except:
            return False
    
    def _generate_api_key(self) -> str:
        """生成API密钥"""
        return f"aicost_{secrets.token_hex(16)}"
    
    def _get_default_quota(self, account_type: str) -> Dict[str, int]:
        """获取默认API配额"""
        quotas = {
            "free": {
                "total_monthly_tokens": 100000,  # 10万token
                "max_requests_per_day": 100,
                "providers": {
                    "DeepSeek": 50000,
                    "OpenAI": 30000,
                    "Baidu Qianfan": 20000
                }
            },
            "pro": {
                "total_monthly_tokens": 1000000,  # 100万token
                "max_requests_per_day": 1000,
                "providers": {
                    "DeepSeek": 400000,
                    "OpenAI": 400000, 
                    "Baidu Qianfan": 200000
                }
            },
            "enterprise": {
                "total_monthly_tokens": 10000000,  # 1000万token
                "max_requests_per_day": 10000,
                "providers": {
                    "DeepSeek": 4000000,
                    "OpenAI": 4000000,
                    "Baidu Qianfan": 2000000
                }
            }
        }
        
        return quotas.get(account_type, quotas["free"])
    
    def register_user(self, 
                     email: str, 
                     username: str, 
                     password: str,
                     account_type: str = "free") -> Optional[User]:
        """注册新用户"""
        # 验证输入
        if not email or not username or not password:
            logger.error("邮箱、用户名和密码不能为空")
            return None
        
        if account_type not in ["free", "pro", "enterprise"]:
            logger.error(f"不支持的账户类型: {account_type}")
            return None
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查是否已存在
            cursor.execute("SELECT COUNT(*) FROM users WHERE email = ? OR username = ?", 
                          (email, username))
            if cursor.fetchone()[0] > 0:
                logger.error("邮箱或用户名已存在")
                return None
            
            # 创建用户
            user_id = f"user_{secrets.token_hex(8)}"
            password_hash = self._hash_password(password)
            api_key = self._generate_api_key()
            now = datetime.now().isoformat()
            
            # 默认配额
            api_quota = self._get_default_quota(account_type)
            
            cursor.execute('''
            INSERT INTO users 
            (user_id, email, username, password_hash, created_at, account_type, 
             api_key, api_quota, monthly_budget, monthly_used, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id, email, username, password_hash, now, account_type,
                api_key, json.dumps(api_quota), 100.0, 0.0, 1
            ))
            
            conn.commit()
            
            user = User(
                user_id=user_id,
                email=email,
                username=username,
                created_at=now,
                last_login=now,
                account_type=account_type,
                api_key=api_key,
                monthly_budget=100.0,
                monthly_used=0.0,
                api_quota=api_quota,
                is_active=True
            )
            
            logger.info(f"用户注册成功: {username} ({account_type})")
            return user
            
        except Exception as e:
            logger.error(f"用户注册失败: {str(e)}")
            return None
        finally:
            conn.close()
    
    def authenticate_user(self, identifier: str, password: str) -> Optional[User]:
        """用户认证"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 通过邮箱或用户名查找
            cursor.execute('''
            SELECT user_id, email, username, password_hash, created_at, last_login,
                   account_type, api_key, monthly_budget, monthly_used, api_quota, 
                   is_active, billing_info
            FROM users 
            WHERE (email = ? OR username = ?) AND is_active = 1
            ''', (identifier, identifier))
            
            row = cursor.fetchone()
            if not row:
                logger.warning(f"用户不存在或已禁用: {identifier}")
                return None
            
            # 验证密码
            if not self._verify_password(password, row[3]):
                logger.warning(f"密码错误: {identifier}")
                return None
            
            # 更新最后登录时间
            now = datetime.now().isoformat()
            cursor.execute("UPDATE users SET last_login = ? WHERE user_id = ?", 
                          (now, row[0]))
            conn.commit()
            
            # 创建用户对象
            user = User(
                user_id=row[0],
                email=row[1],
                username=row[2],
                created_at=row[4],
                last_login=now,
                account_type=row[6],
                api_key=row[7],
                monthly_budget=row[8],
                monthly_used=row[9],
                api_quota=json.loads(row[10]) if row[10] else {},
                is_active=bool(row[11]),
                billing_info=json.loads(row[12]) if row[12] else None
            )
            
            logger.info(f"用户认证成功: {user.username}")
            return user
            
        except Exception as e:
            logger.error(f"用户认证失败: {str(e)}")
            return None
        finally:
            conn.close()
    
    def authenticate_by_api_key(self, api_key: str) -> Optional[User]:
        """通过API密钥认证"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT user_id, email, username, created_at, last_login,
                   account_type, monthly_budget, monthly_used, api_quota, 
                   is_active, billing_info
            FROM users 
            WHERE api_key = ? AND is_active = 1
            ''', (api_key,))
            
            row = cursor.fetchone()
            if not row:
                logger.warning(f"API密钥无效: {api_key[:8]}...")
                return None
            
            user = User(
                user_id=row[0],
                email=row[1],
                username=row[2],
                created_at=row[3],
                last_login=row[4],
                account_type=row[5],
                api_key=api_key,
                monthly_budget=row[6],
                monthly_used=row[7],
                api_quota=json.loads(row[8]) if row[8] else {},
                is_active=bool(row[9]),
                billing_info=json.loads(row[10]) if row[10] else None
            )
            
            return user
            
        except Exception as e:
            logger.error(f"API密钥认证失败: {str(e)}")
            return None
        finally:
            conn.close()
    
    def record_api_usage(self, 
                        user_id: str,
                        provider: str,
                        model: str,
                        input_tokens: int,
                        output_tokens: int,
                        cost: float,
                        request_id: Optional[str] = None) -> bool:
        """记录API使用情况"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查用户预算
            cursor.execute('''
            SELECT monthly_budget, monthly_used 
            FROM users 
            WHERE user_id = ? AND is_active = 1
            ''', (user_id,))
            
            row = cursor.fetchone()
            if not row:
                logger.error(f"用户不存在或已禁用: {user_id}")
                return False
            
            monthly_budget, monthly_used = row
            
            # 检查是否超出预算
            new_total = monthly_used + cost
            if new_total > monthly_budget:
                logger.warning(f"用户 {user_id} 超出预算: {new_total:.2f}/{monthly_budget:.2f}")
                # 可以在这里触发通知或限制访问
            
            # 记录使用情况
            usage_id = f"usage_{secrets.token_hex(8)}"
            now = datetime.now().isoformat()
            
            cursor.execute('''
            INSERT INTO api_usage 
            (usage_id, user_id, provider, model, input_tokens, output_tokens, 
             cost, timestamp, request_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                usage_id, user_id, provider, model, input_tokens, 
                output_tokens, cost, now, request_id
            ))
            
            # 更新用户使用量
            cursor.execute('''
            UPDATE users 
            SET monthly_used = monthly_used + ? 
            WHERE user_id = ?
            ''', (cost, user_id))
            
            conn.commit()
            
            logger.info(f"记录API使用: {user_id} - {provider}:{model} - ¥{cost:.4f}")
            return True
            
        except Exception as e:
            logger.error(f"记录API使用失败: {str(e)}")
            return False
        finally:
            conn.close()
    
    def check_quota(self, user_id: str, provider: str, tokens_needed: int) -> Tuple[bool, str]:
        """检查配额"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT api_quota, account_type 
            FROM users 
            WHERE user_id = ? AND is_active = 1
            ''', (user_id,))
            
            row = cursor.fetchone()
            if not row:
                return False, "用户不存在"
            
            api_quota_json, account_type = row
            api_quota = json.loads(api_quota_json) if api_quota_json else {}
            
            # 检查提供商配额
            provider_quota = api_quota.get("providers", {}).get(provider, 0)
            
            # 计算本月已使用的token（简化版）
            cursor.execute('''
            SELECT SUM(input_tokens + output_tokens) 
            FROM api_usage 
            WHERE user_id = ? AND provider = ?
              AND timestamp >= date('now', 'start of month')
            ''', (user_id, provider))
            
            used_result = cursor.fetchone()
            used_tokens = used_result[0] or 0
            
            if used_tokens + tokens_needed > provider_quota:
                remaining = max(0, provider_quota - used_tokens)
                return False, f"提供商配额不足。剩余: {remaining} tokens"
            
            # 检查总配额
            total_quota = api_quota.get("total_monthly_tokens", 0)
            
            cursor.execute('''
            SELECT SUM(input_tokens + output_tokens) 
            FROM api_usage 
            WHERE user_id = ? 
              AND timestamp >= date('now', 'start of month')
            ''', (user_id,))
            
            total_used_result = cursor.fetchone()
            total_used = total_used_result[0] or 0
            
            if total_used + tokens_needed > total_quota:
                remaining = max(0, total_quota - total_used)
                return False, f"总配额不足。剩余: {remaining} tokens"
            
            return True, "配额充足"
            
        except Exception as e:
            logger.error(f"检查配额失败: {str(e)}")
            return False, f"检查配额时出错: {str(e)}"
        finally:
            conn.close()
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户统计信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 基础信息
            cursor.execute('''
            SELECT username, email, account_type, created_at, last_login,
                   monthly_budget, monthly_used, api_quota
            FROM users 
            WHERE user_id = ?
            ''', (user_id,))
            
            row = cursor.fetchone()
            if not row:
                return {"error": "用户不存在"}
            
            username, email, account_type, created_at, last_login, \
            monthly_budget, monthly_used, api_quota_json = row
            
            api_quota = json.loads(api_quota_json) if api_quota_json else {}
            
            # 本月使用统计
            cursor.execute('''
            SELECT 
                COUNT(*) as api_calls,
                SUM(input_tokens + output_tokens) as total_tokens,
                SUM(cost) as total_cost,
                GROUP_CONCAT(DISTINCT provider) as providers_used
            FROM api_usage 
            WHERE user_id = ? 
              AND timestamp >= date('now', 'start of month')
            ''', (user_id,))
            
            usage_row = cursor.fetchone()
            api_calls, total_tokens, total_cost, providers_used = usage_row
            
            # 每日使用趋势（最近7天）
            cursor.execute('''
            SELECT 
                date(timestamp) as day,
                COUNT(*) as daily_calls,
                SUM(input_tokens + output_tokens) as daily_tokens,
                SUM(cost) as daily_cost
            FROM api_usage 
            WHERE user_id = ? 
              AND timestamp >= date('now', '-7 days')
            GROUP BY date(timestamp)
            ORDER BY day DESC
            ''', (user_id,))
            
            daily_trend = []
            for day_row in cursor.fetchall():
                daily_trend.append({
                    "date": day_row[0],
                    "api_calls": day_row[1] or 0,
                    "tokens": day_row[2] or 0,
                    "cost": day_row[3] or 0.0
                })
            
            # 提供商使用分布
            cursor.execute('''
            SELECT 
                provider,
                COUNT(*) as calls,
                SUM(input_tokens + output_tokens) as tokens,
                SUM(cost) as cost
            FROM api_usage 
            WHERE user_id = ? 
              AND timestamp >= date('now', 'start of month')
            GROUP BY provider
            ''', (user_id,))
            
            provider_dist = {}
            for provider_row in cursor.fetchall():
                provider_dist[provider_row[0]] = {
                    "calls": provider_row[1] or 0,
                    "tokens": provider_row[2] or 0,
                    "cost": provider_row[3] or 0.0
                }
            
            return {
                "user_info": {
                    "username": username,
                    "email": email,
                    "account_type": account_type,
                    "created_at": created_at,
                    "last_login": last_login
                },
                "billing": {
                    "monthly_budget": monthly_budget,
                    "monthly_used": monthly_used or 0.0,
                    "remaining_budget": max(0, monthly_budget - (monthly_used or 0.0)),
                    "usage_percentage": round(((monthly_used or 0.0) / monthly_budget) * 100, 2) if monthly_budget > 0 else 0
                },
                "quota": api_quota,
                "monthly_stats": {
                    "api_calls": api_calls or 0,
                    "total_tokens": total_tokens or 0,
                    "total_cost": total_cost or 0.0,
                    "providers_used": providers_used.split(',') if providers_used else []
                },
                "daily_trend": daily_trend,
                "provider_distribution": provider_dist,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取用户统计失败: {str(e)}")
            return {"error": str(e)}
        finally:
            conn.close()
    
    def upgrade_account(self, user_id: str, new_account_type: str) -> bool:
        """升级账户"""
        if new_account_type not in ["pro", "enterprise"]:
            logger.error(f"无效的账户类型: {new_account_type}")
            return False
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取当前账户类型
            cursor.execute('SELECT account_type FROM users WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            if not row:
                return False
            
            current_type = row[0]
            
            # 检查是否是升级
            account_order = {"free": 0, "pro": 1, "enterprise": 2}
            if account_order.get(new_account_type, 0) <= account_order.get(current_type, 0):
                logger.warning(f"不是有效升级: {current_type} -> {new_account_type}")
                return False
            
            # 更新账户类型和配额
            new_quota = self._get_default_quota(new_account_type)
            
            cursor.execute('''
            UPDATE users 
            SET account_type = ?, api_quota = ?
            WHERE user_id = ?
            ''', (new_account_type, json.dumps(new_quota), user_id))
            
            conn.commit()
            
            logger.info(f"账户升级成功: {user_id} ({current_type} -> {new_account_type})")
            return True
            
        except Exception as e:
            logger.error(f"账户升级失败: {str(e)}")
            return False
        finally:
            conn.close()


# 使用示例
if __name__ == "__main__":
    # 初始化用户管理器
    manager = UserManager()
    
    # 注册测试用户
    print("=== 注册测试用户 ===")
    user = manager.register_user(
        email="test@aicost.com",
        username="testuser",
        password="testpass123",
        account_type="pro"
    )
    
    if user:
        print(f"注册成功: {user.username} ({user.account_type})")
        print(f"API密钥: {user.api_key}")
    
    # 用户认证
    print("\n=== 用户认证 ===")
    auth_user = manager.authenticate_user("testuser", "testpass123")
    if auth_user:
        print(f"认证成功: {auth_user.username}")
    
    # API密钥认证
    print("\n=== API密钥认证 ===")
    if user:
        api_user = manager.authenticate_by_api_key(user.api_key)
        if api_user:
            print(f"API认证成功: {api_user.username}")
    
    # 记录API使用
    print("\n=== 记录API使用 ===")
    if user:
        success = manager.record_api_usage(
            user_id=user.user_id,
            provider="OpenAI",
            model="gpt-4",
            input_tokens=500,
            output_tokens=250,
            cost=0.125
        )
        print(f"记录API使用: {'成功' if success else '失败'}")
    
    # 检查配额
    print("\n=== 检查配额 ===")
    if user:
        has_quota, message = manager.check_quota(user.user_id, "OpenAI", 1000)
        print(f"配额检查: {message}")
    
    # 获取用户统计
    print("\n=== 获取用户统计 ===")
    if user:
        stats = manager.get_user_stats(user.user_id)
        print(f"用户名: {stats['user_info']['username']}")
        print(f"账户类型: {stats['user_info']['account_type']}")
        print(f"本月成本: ¥{stats['monthly_stats']['total_cost']:.2f}")
        print(f"预算使用: {stats['billing']['usage_percentage']}%")