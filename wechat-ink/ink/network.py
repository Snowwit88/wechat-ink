import ipaddress
import os
import requests
from .settings import InkError

class Transport:
    def __init__(self,session=None):
        self.session=session or requests.Session()
        self.session.trust_env=False

    def json(self,method,url,**kwargs):
        try:
            response=self.session.request(method,url,timeout=kwargs.pop('timeout',45),**kwargs)
            response.raise_for_status(); value=response.json()
        except (requests.RequestException,ValueError):
            raise InkError('网络或响应错误；未自动重试写入操作，请核对远端状态后再继续。') from None
        if not isinstance(value,dict): raise InkError('服务返回了非对象响应')
        code=value.get('errcode',0)
        if code: raise InkError(f'微信接口错误码：{code}；请按官方文档排查。')
        if value.get('error'): raise InkError('图片服务返回错误，请检查本机配置与服务额度。')
        return value

def fixed_transport(settings):
    if os.getenv('INK_EGRESS_LAUNCH')!='1': raise InkError('微信操作请通过 operations/wechat-egress.sh 执行')
    e=settings.data.get('egress',{})
    proxy=e.get('proxy','socks5h://127.0.0.1:1088'); expected=e.get('expected_ip','')
    if not proxy.startswith('socks5h://127.0.0.1:'): raise InkError('固定出口必须使用本机 SOCKS5h 通道')
    try: ipaddress.IPv4Address(expected)
    except ipaddress.AddressValueError: raise InkError('请配置预期的固定出口 IPv4') from None
    transport=Transport(); transport.session.proxies={'http':proxy,'https':proxy}
    actual=transport.json('GET','https://api.ipify.org?format=json').get('ip')
    if actual!=expected: raise InkError('出口 IP 不匹配，已停止；不会回退直连')
    return transport
