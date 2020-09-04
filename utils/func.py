from django.core.mail import send_mail
from django.conf import settings
from workflow import models as wfmodels
from django.http import HttpResponseRedirect
from django_redis import get_redis_connection
from ldap3 import Server, Connection, AUTO_BIND_NO_TLS, SUBTREE, BASE, ALL_ATTRIBUTES, ObjectDef, AttrDef, Reader, Entry, Attribute, OperationalAttribute
from django.shortcuts import redirect
import re
import logging
logger = logging.getLogger(__name__)


def Ssologin(function):
    """判断用户是否已经登陆，登陆状态继续访问，没有登陆，跳转到login页面登陆"""

    def _SSO(request, *args, **kwargs):
        if 'is_login' in request.session:
            return function(request, *args, **kwargs)
        else:
            response = HttpResponseRedirect('/login?next=' + request.get_full_path())
            return response

    return _SSO


def approve_check(func):
    def wrapper(request, ticket_id, *args, **kwargs):
        try:
            ticket = wfmodels.Ticket.objects.get(ticket_id=ticket_id)
        except wfmodels.Ticket.DoesNotExist as e:
            logging.error(e)
            return redirect("ticket_pending")
        allusers = [i.username for i in wfmodels.Role.objects.filter(node_id=ticket.current_node)]
        if request.session.get('user') in allusers:
            return func(request, ticket_id, *args, **kwargs)
        else:
            return redirect('ticket_pending')
    return wrapper


def admin_check(function):
    conn = get_redis_connection('default')
    admin_users = conn.smembers('admin_users')
    admin_usersli = [i.decode() for i in admin_users]

    def wrapper(request, *args, **kwargs):
        if request.session.get('user') in admin_usersli:
            return function(request, *args, **kwargs)
        else:
            return redirect('/')
    return wrapper


def sendmail(to_email, info):
    subject = '工单系统提示信息'
    message = ''
    sender = settings.EMAIL_FROM
    html_message = '<p>%s</p>' % str(info)
    if not re.match(r'.*@{}$'.format(settings.EMAIL_SUFFIX), to_email):
        to_email = to_email + '@' + settings.EMAIL_SUFFIX
    receiver = [to_email]
    logging.info(receiver)
    send_mail(subject, message, sender, receiver, html_message=html_message)


def reb(res, status):
    """
    构造Json字典
    :param res:
    :param status:
    :return:
    """
    data = {}
    if status == 0:
        data['Msg'] = "Success"
    else:
        data['Msg'] = "Failed"
    data['Result'] = res
    data['Status'] = status
    return data


def ldapsearch():
    conn = Connection(Server(settings.LDAP_SERVER, port=settings.LDAP_PORT, use_ssl=False), auto_bind=AUTO_BIND_NO_TLS, user=settings.LDAP_USER,
                      password=settings.LDAP_PASSWORD)
    conn.search(
        search_base=settings.LDAP_BASE_DN,
        search_filter='(objectClass=group)',
        search_scope=SUBTREE,
        attributes=['member']
    )
    allusers = []
    for entry in conn.entries:
        for member in entry.member.values:
            conn.search(
                search_base=settings.LDAP_BASE_DN,
                search_filter=f'(distinguishedName={member})',
                attributes=[
                    'sAMAccountName'
                ]
            )
            try:
                user_sAMAccountName = conn.entries[0].sAMAccountName.values[0]
                allusers.append(user_sAMAccountName)
                allusers = list(set(allusers))
            except Exception as e:
                pass
    return allusers