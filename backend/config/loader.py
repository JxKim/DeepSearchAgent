"""
配置加载器 - 加载YAML配置和环境变量
"""
import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

from config.models import AppConfig
class ConfigLoader:
    """配置加载器类"""
    
    def __init__(self, config_path: str = str(Path(__file__).parent.parent / "config.yaml"), env_path: str = ".env"):
        self.config_path = Path(config_path)
        self.env_path = Path(env_path)
        self._config: Optional[AppConfig] = None
    
    def load_environment_variables(self) -> None:
        """加载环境变量"""
        # 优先加载.env文件
        if self.env_path.exists():
            load_dotenv(self.env_path)
        
        # 设置环境变量默认值
        os.environ.setdefault("ENVIRONMENT", "development")
        os.environ.setdefault("DEBUG", "true")
    
    def parse_yaml_config(self) -> Dict[str, Any]:
        """解析YAML配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config_content = f.read()
        
        # 替换环境变量占位符
        config_content = self._replace_env_variables(config_content)
        
        return yaml.safe_load(config_content) or {}
    
    def _replace_env_variables(self, content: str) -> str:
        """替换环境变量占位符"""
        import re
        
        def replace_match(match):
            var_name = match.group(1)
            default_value = match.group(2) if match.group(2) else None
            
            # 获取环境变量值
            env_value = os.getenv(var_name)
            
            if env_value is not None:
                return env_value
            elif default_value is not None:
                return default_value
            else:
                # 如果没有环境变量且没有默认值，保持原样
                return match.group(0)
        
        # 匹配 ${VAR_NAME} 或 ${VAR_NAME:default_value} 格式
        pattern = r'\$\{([A-Za-z0-9_]+)(?::([^}]*))?\}'
        return re.sub(pattern, replace_match, content)
    
    def get_config(self) -> AppConfig:
        """获取配置实例"""
        if self._config is None:
            self._config = self._load_config()
        return self._config
    
    def _load_config(self) -> AppConfig:
        """加载配置"""
        # 加载环境变量
        self.load_environment_variables()
        
        # 解析YAML配置
        yaml_config = self.parse_yaml_config()
        
        # 合并环境变量到配置
        config_dict = self._merge_with_environment(yaml_config)
        
        # 转换为Pydantic模型
        return AppConfig(**config_dict)
    
    def _merge_with_environment(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """将环境变量合并到配置中"""
        # todo 不需要合并环境变量到配置中
        # 环境变量优先级高于YAML配置
        
        # 基础配置
        if os.getenv("ENVIRONMENT"):
            config["environment"] = os.getenv("ENVIRONMENT")
        if os.getenv("DEBUG"):
            config["debug"] = os.getenv("DEBUG").lower() == "true"
        
        # 飞书配置
        if "feishu" in config:
            if os.getenv("FEISHU_APP_ID"):
                config["feishu"]["app_id"] = os.getenv("FEISHU_APP_ID")
            if os.getenv("FEISHU_APP_SECRET"):
                config["feishu"]["app_secret"] = os.getenv("FEISHU_APP_SECRET")
        
        # LLM配置
        if "llm" in config:
            if os.getenv("LLM_API_KEY"):
                config["llm"]["api_key"] = os.getenv("LLM_API_KEY")
            if os.getenv("LLM_BASE_URL"):
                config["llm"]["base_url"] = os.getenv("LLM_BASE_URL")
        
        # 安全配置
        if "security" in config:
            if os.getenv("JWT_SECRET_KEY"):
                config["security"]["secret_key"] = os.getenv("JWT_SECRET_KEY")
        
        # 数据库配置（可选）
        if os.getenv("DATABASE_URL"):
            config.setdefault("database", {})["url"] = os.getenv("DATABASE_URL")
        if os.getenv("DATABASE_ECHO"):
            config.setdefault("database", {})["echo"] = os.getenv("DATABASE_ECHO").lower() == "true"
        
        # 服务器配置（可选）
        if os.getenv("SERVER_HOST"):
            config.setdefault("server", {})["host"] = os.getenv("SERVER_HOST")
        if os.getenv("SERVER_PORT"):
            config.setdefault("server", {})["port"] = int(os.getenv("SERVER_PORT"))
        if os.getenv("SERVER_WORKERS"):
            config.setdefault("server", {})["workers"] = int(os.getenv("SERVER_WORKERS"))
        if os.getenv("SERVER_RELOAD"):
            config.setdefault("server", {})["reload"] = os.getenv("SERVER_RELOAD").lower() == "true"
        
        return config
    
    def reload(self) -> None:
        """重新加载配置"""
        self._config = None
        self.get_config()


# 全局配置实例
_config_loader = ConfigLoader()


def get_config() -> AppConfig:
    """获取全局配置实例"""
    return _config_loader.get_config()


def reload_config() -> None:
    """重新加载配置"""
    _config_loader.reload()


def init_config(config_path: str = "config/config.yaml", env_path: str = ".env") -> None:
    """初始化配置（用于测试或自定义配置路径）"""
    global _config_loader
    _config_loader = ConfigLoader(config_path, env_path)

if __name__ == "__main__":
    config = get_config()
    print(config.feishu.app_id)
