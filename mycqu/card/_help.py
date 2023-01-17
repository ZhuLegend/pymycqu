import json
from html.parser import HTMLParser
import requests
from mycqu.exception import TicketGetError, ParseError, CQUWebsiteError


class _CardPageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self._starttag: bool = False
        self.ssoticket_id: str = ""

    def handle_starttag(self, tag, attrs):
        if not self._starttag and tag == 'input' and ('name', 'ssoticketid') in attrs:
            self._starttag = True
            for key, val in attrs:
                if key == "value":
                    self.ssoticket_id = val
                    break


# 获取hallticket
def _get_hall_ticket(session, ssoticket_id):
    url = 'http://card.cqu.edu.cn/cassyno/index'
    data = {
        'errorcode': '1',
        'continueurl': 'http://card.cqu.edu.cn/cassyno/index',
        'ssoticketid': ssoticket_id,
    }
    r = session.post(url, data=data)
    if r.status_code != 200:
        raise CQUWebsiteError()
    return session


# 利用登录之后的cookie获取一卡通的关键ticket
def _get_ticket(session):
    url = 'http://card.cqu.edu.cn/Page/Page'
    data = {
        'EMenuName': '电费、网费',
        'MenuName': '电费、网费',
        'Url': 'http%3a%2f%2fcard.cqu.edu.cn%3a8080%2fblade-auth%2ftoken%2fthirdToToken%2ffwdt',
        'apptype': '4',
        'flowID': '10002'
    }
    r = session.post(url, data=data)
    if r.status_code != 200:
        raise CQUWebsiteError()
    ticket_start = r.text.find('ticket=')
    if ticket_start > 0:
        ticket_end = r.text.find("'", ticket_start)
        ticket = r.text[ticket_start + len('ticket='): ticket_end]
        return ticket
    else:
        raise TicketGetError()


# 利用ticket获取一卡通关键cookie
def _get_synjones_auth(ticket):
    url = 'http://card.cqu.edu.cn:8080/blade-auth/token/fwdt'
    data = {'ticket': ticket}
    r = requests.post(url, data=data)
    if r.status_code != 200:
        raise CQUWebsiteError()
    try:
        dic = json.loads(r.text)
        token = dic['data']['access_token']
    except:
        raise ParseError()
    else:
        return 'bearer ' + token


# 利用关键cookie获取水电费dic
def _get_fee_data(synjones_auth, room, fee_item_id):
    url = "http://card.cqu.edu.cn:8080/charge/feeitem/getThirdData"
    data = {
        'feeitemid': fee_item_id,
        'json': 'true',
        'level': '2',
        'room': room,
        'type': 'IEC',
    }
    cookie = {'synjones-auth': synjones_auth}
    r = requests.post(url, data=data, cookies=cookie)
    if r.status_code != 200:
        raise CQUWebsiteError()
    dic = json.loads(r.text)
    if dic['msg'] == 'success':
        return dic
    else:
        raise CQUWebsiteError(dic['msg'])
