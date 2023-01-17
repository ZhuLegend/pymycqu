from typing import Optional, Callable
from requests import Session, Response

from ._authserver import *
from ._sso import *


__all__ = ("is_sso_logined", "is_authserver_logined", 'is_logined',
           "logout_sso", "logout_authserver", 'logout',
           "access_sso_service", "access_authserver_service", 'access_service',
           "login_sso", "login_authserver", 'login',
           'AuthserverAuthorizer', 'SSOAuthorizer')


def is_logined(session: Session, use_sso: bool = True) -> bool:
    """判断是否处于统一身份认证登陆状态

    :param session: 会话
    :type session: Session
    :param use_sso: 是否使用 sso 而非 authserver, 默认为 :obj::`True`
    :type use_sso: bool, optional
    :return: :obj:`True` 如果处于登陆状态，:obj:`False` 如果处于未登陆或登陆过期状态
    :rtype: bool
    """
    return SSOAuthorizer.is_logined(session) if use_sso else AuthserverAuthorizer.is_logined(session)


def logout(session: Session, use_sso: bool = True) -> None:
    """注销统一身份认证登录状态

    :param session: 进行过登录的会话
    :type session: Session
    :param use_sso: 是否使用 sso 而非 authserver, 默认为 :obj::`True`
    :type use_sso: bool, optional
    """
    SSOAuthorizer.logout(session) if use_sso else AuthserverAuthorizer.logout(session)


def access_service(session: Session, service: str, use_sso: bool = True) -> Response:
    """从登录了统一身份认证（authserver）的会话获取指定服务的许可

    :param session: 登录了统一身份认证的会话
    :type session: Session
    :param service: 服务的 url
    :type service: str
    :param use_sso: 是否使用 sso 而非 authserver, 默认为 :obj::`True`
    :type use_sso: bool, optional
    :raises NotLogined: 统一身份认证未登录时抛出
    :return: 访问服务 url 的 :class:`Response`
    :rtype: Response
    """
    return SSOAuthorizer.access_service(session, service) if use_sso else AuthserverAuthorizer.access_service(session, service)


def login(session: Session,
          username: str,
          password: str,
          service: Optional[str] = None,
          timeout: int = 10,
          force_relogin: bool = False,
          captcha_callback: Optional[
              Callable[[bytes, str], Optional[str]]] = None,
          keep_longer: bool = False,
          kick_others: bool = False,
          use_sso: bool = True
          ) -> Response:
    """登录统一身份认证

    :param session: 用于登录统一身份认证的会话
    :type session: Session
    :param username: 统一身份认证号或学工号
    :type username: str
    :param password: 统一身份认证密码
    :type password: str
    :param service: 需要登录的服务，默认（:obj:`None`）则先不登陆任何服务
    :type service: Optional[str], optional
    :param timeout: 连接超时时限，默认为 10（单位秒）
    :type timeout: int, optional
    :param force_relogin: 强制重登，当会话中已经有有效的登陆 cookies 时依然重新登录，默认为 :obj:`False`
    :type force_relogin: bool, optional
    :param captcha_callback: 需要输入验证码时调用的回调函数，默认为 :obj:`None` 即不设置回调；
                             当需要输入验证码，但回调没有设置或回调返回 :obj:`None` 时，抛出异常 :class:`NeedCaptcha`；
                             该函数接受一个 :class:`bytes` 型参数为验证码图片的文件数据，一个 :class:`str` 型参数为图片的 MIME 类型，
                             返回验证码文本或 :obj:`None`。
    :type captcha_callback: Optional[Callable[[bytes, str], Optional[str]]], optional
    :param keep_longer: 保持更长时间的登录状态（保持一周）
    :type keep_longer: bool
    :param kick_others: 当目标用户开启了“单处登录”并有其他登录会话时，踢出其他会话并登录单前会话；若该参数为 :obj:`False` 则抛出
                       :class:`MultiSessionConflict`
    :type kick_others: bool
    :param use_sso: 是否使用 sso 而非 authserver, 默认为 :obj::`True`
    :type use_sso: bool, optional
    :raises UnknownAuthserverException: 未知认证错误
    :raises InvaildCaptcha: 无效的验证码
    :raises IncorrectLoginCredentials: 错误的登陆凭据（如错误的密码、用户名）
    :raises NeedCaptcha: 需要提供验证码，获得验证码文本之后可调用所抛出异常的 :func:`NeedCaptcha.after_captcha` 函数来继续登陆
    :raises MultiSessionConflict: 和其他会话冲突
    :return: 登陆了统一身份认证后所跳转到的地址的 :class:`Response`
    :rtype: Response
    """
    return SSOAuthorizer.login(session, username, password, service, timeout, force_relogin, captcha_callback, keep_longer, kick_others) \
        if use_sso else AuthserverAuthorizer.login(session, username, password, service, timeout, force_relogin, captcha_callback, keep_longer, kick_others)
