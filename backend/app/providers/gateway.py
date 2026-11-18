"""供问答服务访问本机模型网关的客户端。"""

from app.providers.deepseek import OpenAIChat


class GatewayChat(OpenAIChat):
    """通过 OpenAI 兼容接口访问网关中的模型别名。"""

    provider_name = "模型网关"
    api_key_name = "GATEWAY_API_KEY"
