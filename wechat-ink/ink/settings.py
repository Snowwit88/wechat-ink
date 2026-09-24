from dataclasses import dataclass
from pathlib import Path
from typing import Any
import os
import yaml

ROOT = Path(__file__).resolve().parents[1]
class InkError(Exception):
    """A user-readable error that never contains credentials."""

@dataclass
class Settings:
    path: Path
    data: dict[str, Any]
    account_name: str
    account: dict[str, Any]

    @classmethod
    def read(cls, path=None, account=None, optional=False):
        location=Path(path or os.getenv('WECHAT_INK_CONFIG', ROOT/'wechat-ink.yaml')).expanduser().resolve()
        if not location.exists():
            if not optional: raise InkError(f'配置文件不存在：{location}')
            data={}
        else:
            try: data=yaml.safe_load(location.read_text(encoding='utf-8')) or {}
            except (yaml.YAMLError,OSError): raise InkError('配置无法读取或 YAML 格式错误') from None
        if not isinstance(data,dict): raise InkError('配置顶层必须是映射')
        accounts=data.get('accounts',{})
        if not isinstance(accounts,dict): raise InkError('accounts 必须是映射')
        name=account or data.get('default','main')
        if name not in accounts and (account or accounts): raise InkError(f'账号未配置：{name}')
        value=accounts.get(name,{})
        if not isinstance(value,dict): raise InkError('账号配置必须是映射')
        return cls(location,data,str(name),value)

    def image(self):
        value=dict(self.data.get('image_generation',{}).get('openai',{}))
        for field, env in [('api_key','OPENAI_API_KEY'),('base_url','OPENAI_BASE_URL'),('image_model','OPENAI_IMAGE_MODEL')]:
            if os.getenv(env): value[field]=os.environ[env]
        return value

    def check(self):
        image=self.image()
        return {'account':self.account_name, 'wechat_credentials_present':all(self.account.get(k) for k in ('app_id','app_secret')),
                'image_credentials_present':bool(image.get('api_key')), 'image_endpoint_present':bool(image.get('base_url')),
                'egress_configured':bool(self.data.get('egress',{}).get('expected_ip'))}
