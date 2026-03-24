"""
LangChain集成 - AICostMonitor Callback Handler
用于追踪LangChain API调用成本
"""

from typing import Any, Dict, Optional, List
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import AgentAction, AgentFinish, LLMResult


class AICostMonitorCallback(BaseCallbackHandler):
    """LangChain成本追踪回调"""
    
    def __init__(
        self,
        api_url: str = "http://localhost:8000",
        user_id: str = "langchain_user",
        track_tokens: bool = True
    ):
        super().__init__()
        self.api_url = api_url
        self.user_id = user_id
        self.track_tokens = track_tokens
        self.call_count = 0
        self.total_tokens = 0
        self.total_cost = 0.0
    
    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        **kwargs: Any
    ) -> None:
        """LLM调用开始"""
        self.call_count += 1
    
    def on_llm_end(
        self,
        response: LLMResult,
        **kwargs: Any
    ) -> None:
        """LLM调用结束"""
        if not self.track_tokens:
            return
        
        # 尝试获取token使用情况
        try:
            if response.llm_output and 'token_usage' in response.llm_output:
                usage = response.llm_output['token_usage']
                self.total_tokens += usage.get('total_tokens', 0)
                
                # 计算成本（简化版）
                cost = self._estimate_cost(usage)
                self.total_cost += cost
                
                # 发送到服务器
                self._send_to_server(usage)
        except Exception:
            pass
    
    def _estimate_cost(self, usage: Dict) -> float:
        """估算成本（需要根据实际模型调整）"""
        # 简化估算：假设GPT-4价格
        prompt_tokens = usage.get('prompt_tokens', 0)
        completion_tokens = usage.get('completion_tokens', 0)
        
        # GPT-4 价格（大约）
        prompt_cost = prompt_tokens * 0.03 / 1000  # $0.03/1K tokens
        completion_cost = completion_tokens * 0.06 / 1000  # $0.06/1K tokens
        
        return prompt_cost + completion_cost
    
    def _send_to_server(self, usage: Dict):
        """发送使用数据到服务器"""
        try:
            import requests
            requests.post(
                f"{self.api_url}/api/record",
                data={
                    "provider": "openai",
                    "model": "gpt-4",  # 需要从response中提取
                    "user_id": self.user_id,
                    "input_tokens": usage.get('prompt_tokens', 0),
                    "output_tokens": usage.get('completion_tokens', 0),
                },
                timeout=2
            )
        except Exception:
            pass
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "call_count": self.call_count,
            "total_tokens": self.total_tokens,
            "total_cost_usd": self.total_cost,
        }


# 便捷函数
def create_callback(
    api_url: str = "http://localhost:8000",
    user_id: str = "langchain_user"
) -> AICostMonitorCallback:
    """创建回调处理器"""
    return AICostMonitorCallback(api_url=api_url, user_id=user_id)
