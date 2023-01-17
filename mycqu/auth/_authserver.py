from typing import Optional, Dict
from functools import partial

from requests import Session, Response

from ._authorizer import Authorizer
from ..exception import UnknownAuthserverException, MultiSessionConflict, ParseError
from ._page_parser import _LoginedPageParser, _get_formdata
from ..utils.deprecated import deprecated

AUTHSERVER_CAPTCHA_DETERMINE_URL = "http://authserver.cqu.edu.cn/authserver/needCaptcha.html"
AUTHSERVER_CAPTCHA_IMAGE_URL = "http://authserver.cqu.edu.cn/authserver/captcha.html"

__all__ = ['is_authserver_logined', 'logout_authserver', 'login_authserver', 'access_authserver_service',
           'AUTHSERVER_CAPTCHA_DETERMINE_URL', 'AUTHSERVER_CAPTCHA_IMAGE_URL', 'AuthserverAuthorizer']

@deprecated('请改用`AuthserverAuthorizer.is_logined`')
def is_authserver_logined(session: Session) -> bool:
    """判断是否处于统一身份认证（authserver）登陆状态

    :param session: 会话
    :type session: Session
    :return: :obj:`True` 如果处于登陆状态，:obj:`False` 如果处于未登陆或登陆过期状态
    :rtype: bool
    """
    return AuthserverAuthorizer.is_logined(session)

@deprecated('请改用`AuthserverAuthorizer.logout`')
def logout_authserver(session: Session) -> None:
    """注销统一身份认证登录（authserver）状态

    :param session: 进行过登录的会话
    :type session: Session
    """
    AuthserverAuthorizer.logout(session)

@deprecated('请改用`AuthserverAuthorizer.access_service`')
def access_authserver_service(session: Session, service: str) -> Response:
    """从登录了统一身份认证（authserver）的会话获取指定服务的许可

    :param session: 登录了统一身份认证的会话
    :type session: Session
    :param service: 服务的 url
    :type service: str
    :raises NotLogined: 统一身份认证未登录时抛出
    :return: 访问服务 url 的 :class:`Response`
    :rtype: Response
    """
    AuthserverAuthorizer.access_service(session, service)

class AuthserverAuthorizer(Authorizer):
    LOGIN_URL = "http://authserver.cqu.edu.cn/authserver/login"
    LOGOUT_URL = "http://authserver.cqu.edu.cn/authserver/logout"

    def _get_request_data(self) -> Dict:
        get_login_page = partial(self.session.get,
                                 url=self.LOGIN_URL,
                                 params=None if self.service is None else {"service": self.service},
                                 allow_redirects=False,
                                 timeout=self.timeout)
        login_page = get_login_page()
        if login_page.status_code == 302:
            if not self.force_relogin:
                return login_page
            else:
                logout_authserver(self.session)
                login_page = get_login_page()
        elif login_page.status_code != 200:
            raise UnknownAuthserverException()

        try:
            formdata = _get_formdata(login_page.text, self.username, self.password)
        except ParseError:
            logout_authserver(self.session)
            formdata = _get_formdata(get_login_page().text, self.username, self.password)
        if self.keep_longer:
            formdata['rememberMe'] = 'on'

        if "captchaResponse" in formdata:
            del formdata["captchaResponse"]

        return formdata

    def _need_captcha(self) -> Optional[str]:
        if self.session.get(AUTHSERVER_CAPTCHA_DETERMINE_URL, params={"username": self.username}).text == "true":
            return AUTHSERVER_CAPTCHA_IMAGE_URL
        else:
            return

    def _need_captcha_handler(self, captcha: str, request_data: Dict):
        request_data["captchaResponse"] = request_data

    def _redirect_to_service(self, login_resp: Response):
        return self.session.get(url=login_resp.headers['Location'], allow_redirects=False)

    def _handle_login_error(self, login_resp: Response):
        parser = _LoginedPageParser(login_resp.status_code)
        parser.feed(login_resp.text)

        if parser._kick:  # pylint: ignore disable=protected-access
            def kick():
                # pylint: ignore disable=protected-access
                login_resp = self.session.post(
                    url=self.LOGIN_URL,
                    data={"execution": parser._kick_execution,
                          "_eventId": "continue"},
                    allow_redirects=False,
                    timeout=self.timeout)
                return self._redirect_to_service(login_resp)

            if self.kick_others:
                return kick()
            else:
                def cancel():
                    # pylint: ignore disable=protected-access
                    return self.session.post(
                        url=self.LOGIN_URL,
                        data={"execution": parser._cancel_execution,
                              "_eventId": "cancel"},
                        allow_redirects=False,
                        timeout=self.timeout)

                raise MultiSessionConflict(kick=kick, cancel=cancel)
        raise UnknownAuthserverException(
            f"status code {login_resp.status_code} is got (302 expected) when sending login post, "
            "but can not find the element span.login_auth_error#msg")

    def _login(self, request_data: Dict) -> Response:
        login_resp = self.session.post(
            url=self.LOGIN_URL, data=request_data, allow_redirects=False)

        if login_resp.status_code != 302:
            return self._handle_login_error(login_resp)
        return self._redirect_to_service(login_resp)


@deprecated('请改用`AuthserverAuthorizer.login`')
def login_authserver(
        session: Session, username: str, password: str, service: Optional[str] = None,
        timeout: int = 10, force_relogin: bool = False, keep_longer: bool = False, kick_others: bool = False) -> Response:
    """登录统一身份认证（authserver）

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
    :param keep_longer: 保持更长时间的登录状态（保持一周）
    :type keep_longer: bool
    :param kick_others: 当目标用户开启了“单处登录”并有其他登录会话时，踢出其他会话并登录单前会话；若该参数为 :obj:`False` 则抛出
                       :class:`MultiSessionConflict`
    :type kick_others: bool
    :raises UnknownAuthserverException: 未知认证错误
    :raises InvaildCaptcha: 无效的验证码
    :raises IncorrectLoginCredentials: 错误的登陆凭据（如错误的密码、用户名）
    :raises NeedCaptcha: 需要提供验证码，获得验证码文本之后可调用所抛出异常的 :func:`NeedCaptcha.after_captcha` 函数来继续登陆
    :raises MultiSessionConflict: 和其他会话冲突
    :return: 登陆了统一身份认证后所跳转到的地址的 :class:`Response`
    :rtype: Response
    """
    return AuthserverAuthorizer._base_login(session, username, password, service, timeout, force_relogin, keep_longer, kick_others)
