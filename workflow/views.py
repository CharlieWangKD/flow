from django.shortcuts import render, redirect

# Create your views here.

from django.views.generic import View
from django_redis import get_redis_connection
from django.http import JsonResponse, QueryDict, HttpResponseRedirect
from workflow import models as wfmodels
from django.db import transaction
from django.db.models import Q, F
import requests
from utils.func import Ssologin, approve_check, reb, sendmail, ldapsearch, admin_check
from utils.pageinator_tools import pageinator_tool
import uuid
import time
import json
from django.utils.decorators import method_decorator
from django.conf import settings
import logging
logger = logging.getLogger(__name__)


def login(request):
    # TODO: update sso login func here
    ref = request.GET.get('ref')
    uid = request.GET.get('uid')
    if ref and not uid:
        logging.info(request.get_raw_uri())
        response = HttpResponseRedirect(settings.SSO_URL + request.get_raw_uri())
        return response

    if uid and ref:
        user_request = requests.get(settings.SSO_URL, params={"uid": uid})
        user_json = user_request.json()
        logging.info(user_json)
        if user_json:
            request.session['is_login'] = True
            request.session.set_expiry(60 * 24 * 60)
            return HttpResponseRedirect(ref)
        else:
            response = HttpResponseRedirect(
                settings.SSO_URL + request.get_raw_uri())
            return response
    return HttpResponseRedirect('/')


def logout(request):
    if not request.session.get('is_login', None):
        return HttpResponseRedirect("/")
    request.session.flush()
    return HttpResponseRedirect('/')


class CreateTestTicket(View):

    @method_decorator(Ssologin)
    def get(self, request):
        return render(request, 'index.html')

    @method_decorator(Ssologin)
    def post(self, request):
        title = request.POST.get('title')
        type = request.POST.get('type')
        ticket_detail = {"title": title}
        logging.info(ticket_detail)
        save_id = transaction.savepoint()
        with transaction.atomic():
            try:
                ticket_id = uuid.uuid1()
                tickettype = wfmodels.TicketType.objects.get(type_name=type)
                init_node = wfmodels.Node.objects.get(name='申请')
                next_node = wfmodels.Flow.objects.get(flow_id__flow_id=tickettype.flow_id, node_id=init_node).child_node_id
                created_tic = wfmodels.Ticket.objects.create(
                    ticket_name='工单申请_%s' % str(int(time.time())),
                    ticket_id=ticket_id,
                    ticket_type=tickettype,
                    current_node=next_node,
                    ticket_status=2,
                    applicant=request.session.get('user'),
                )
                wfmodels.Ticket_detail.objects.create(
                    ticket_id=created_tic,
                    ticket_detail=json.dumps(ticket_detail)
                )
                wfmodels.Participation_info.objects.create(
                    ticket_id=created_tic,
                    node_id=init_node,
                    participant=request.session.get('user'),
                    suggestion=request.POST.get('apply_reason')
                )
                res = "工单已提交."
            except Exception as e:
                logging.error(e)
                transaction.savepoint_rollback(save_id)
                res = "System error."
        return render(request, 'index.html', {'data': res})


class Myticket(View):

    @method_decorator(Ssologin)
    def get(self, request, ticstatus, page):
        q = request.GET.get('q')
        ticstatus = int(ticstatus)
        if not ticstatus in [2, 3, 4]:
            return render(request, 'myticket.html', {'data': 'type error'})
        ticlist = wfmodels.Ticket.objects.filter(applicant=request.session.get('user'), ticket_status=ticstatus).order_by('-update_time')
        if q:
            ticlist = ticlist.filter(Q(ticket_id__contains=q) | Q(ticket_name__contains=q) | Q(applicant__contains=q)).order_by('-update_time')
        ticpages, pages = pageinator_tool(ticlist, page)
        context = {
            'ticstatus': ticstatus,
            'allpage': ticpages,
            'pages': pages
        }
        return render(request, 'myticket.html', context)


class TicketDetail(View):

    @method_decorator(Ssologin)
    def get(self, request, ticket_id):
        context = {}
        try:
            ticket = wfmodels.Ticket.objects.get(ticket_id=ticket_id)
            ticket_info = wfmodels.Ticket_detail.objects.get(ticket_id=ticket)
            if ticket.ticket_status == 2:
                curr_li = wfmodels.Role.objects.filter(node_id__name=ticket.current_node.name)
                ticket.current_user = ','.join([i.username for i in curr_li])
                node = wfmodels.Node.objects.get(name='申请')
                currnode = wfmodels.Flow.objects.get(flow_id__flow_id=ticket.ticket_type.flow_id, node_id=node)
                nodes = [currnode.node_id]
                while currnode.child_node_id:
                    nodes.append(currnode.child_node_id)
                    currnode = wfmodels.Flow.objects.get(flow_id__flow_id=ticket.ticket_type.flow_id, node_id=currnode.child_node_id)
                for n in nodes:
                    n.status = wfmodels.Participation_info.objects.filter(ticket_id=ticket, node_id__name=n.name).first()
                ticket.currstatuscount = len(wfmodels.Participation_info.objects.filter(ticket_id=ticket))
            else:
                nodes = wfmodels.Participation_info.objects.filter(ticket_id=ticket).order_by('update_time')
        except Exception as e:
            logging.error(e)
            context['data'] = 'Get ticket detail failed.'
            return render(request, 'ticket_detail.html', context)
        context['ticket'] = ticket
        context['ticket_info'] = json.loads(ticket_info.ticket_detail)
        context['nodes'] = nodes
        return render(request, 'ticket_detail.html', context)


class TicketDetailApprove(View):

    @method_decorator(Ssologin)
    @method_decorator(approve_check)
    def get(self, request, ticket_id):
        context = {}
        try:
            ticket = wfmodels.Ticket.objects.get(ticket_id=ticket_id)
            ticket_info = wfmodels.Ticket_detail.objects.get(ticket_id=ticket)
            if ticket.ticket_status == 2:
                node = wfmodels.Node.objects.get(name='申请')
                currnode = wfmodels.Flow.objects.get(flow_id__flow_id=ticket.ticket_type.flow_id, node_id=node)
                nodes = [currnode.node_id]
                while currnode.child_node_id:
                    nodes.append(currnode.child_node_id)
                    currnode = wfmodels.Flow.objects.get(flow_id__flow_id=ticket.ticket_type.flow_id,
                                                         node_id=currnode.child_node_id)
                for n in nodes:
                    n.status = wfmodels.Participation_info.objects.filter(ticket_id=ticket, node_id__name=n.name).first()
                ticket.currstatuscount = len(wfmodels.Participation_info.objects.filter(ticket_id=ticket))
            else:
                nodes = wfmodels.Participation_info.objects.filter(ticket_id=ticket).order_by('update_time')
        except wfmodels.Ticket.DoesNotExist:
            context['data'] = 'Get ticket detail failed.'
            return render(request, 'ticket_detail_approve.html', context)
        context['ticket'] = ticket
        context['ticket_info'] = json.loads(ticket_info.ticket_detail)
        context['nodes'] = nodes
        return render(request, 'ticket_detail_approve.html', context)


class TicketUpdate(View):

    @method_decorator(Ssologin)
    def put(self, request):
        data = QueryDict(request.body)
        ticket_id = data.get('ticket_id')
        approve = data.get('approve')
        suggestion = data.get('suggestion')
        logging.info(ticket_id, approve)
        if not all([ticket_id, approve]):
            logging.error(ticket_id, approve)
            return JsonResponse(reb('Params Error.', 1))
        try:
            ticket = wfmodels.Ticket.objects.get(ticket_id=ticket_id)
        except wfmodels.Ticket.DoesNotExist as e:
            logging.error(e)
            return JsonResponse(reb('Get ticket failed.', 1))
        user = request.session.get('user')
        allusers = [i.username for i in wfmodels.Role.objects.filter(node_id=ticket.current_node)]
        if user not in allusers:
            return JsonResponse(reb('No Permission.', 1))
        save_id = transaction.savepoint()
        if not int(approve):
            with transaction.atomic():
                try:
                    ticket = wfmodels.Ticket.objects.select_for_update().get(id=ticket.id)
                    node_last = wfmodels.Participation_info.objects.create(
                        ticket_id=ticket,
                        node_id=ticket.current_node,
                        participant=user,
                        suggestion=suggestion
                    )
                    next_node = wfmodels.Flow.objects.get(flow_id__flow_id=ticket.ticket_type.flow_id,
                                                          node_id=ticket.current_node)
                    ticket.current_node = next_node.child_node_id
                    ticket_info = wfmodels.Ticket_detail.objects.get(ticket_id=ticket)
                    next_node = wfmodels.Flow.objects.get(flow_id__flow_id=ticket.ticket_type.flow_id,
                                                          node_id=ticket.current_node)
                    if not next_node.child_node_id:
                        ticket.ticket_status = 3
                        if ticket.ticket_type.type_name == "type_you_define":
                            # 丢给状态机处理
                            match = Match()
                            match.work()
                            if match.do(ticket_info.ticket_detail):
                                node_last.delete()
                                return JsonResponse(reb('System Error.', 1))

                        # TODO: add others ticket logic

                        logging.info('ticket done.')
                        wfmodels.Participation_info.objects.create(
                            ticket_id=ticket,
                            node_id=wfmodels.Node.objects.get(name='完成'),
                            participant='system',
                            suggestion='approve'
                        )
                    ticket.save()
                    sendmail(ticket.applicant, '工单已通过，工单id: %s' % ticket_id)
                except Exception as e:
                    logging.error(e)
                    transaction.savepoint_rollback(save_id)
                    return JsonResponse(reb('Process failed.', 1))
            return JsonResponse(reb('Approve Done.', 0))
        else:
            with transaction.atomic():
                try:
                    wfmodels.Participation_info.objects.create(
                        ticket_id=ticket,
                        node_id=ticket.current_node,
                        participant=user,
                        suggestion=suggestion
                    )
                    ticket.current_node = wfmodels.Node.objects.get(name='驳回')
                    ticket.ticket_status = 4
                    ticket.save()
                    wfmodels.Participation_info.objects.create(
                        ticket_id=ticket,
                        node_id=ticket.current_node,
                        participant='system',
                        suggestion='rejected',
                        status=False
                    )
                    sendmail(ticket.applicant, '工单已被驳回，工单id: %s, 详情请联系管理员' % ticket_id)
                except Exception as e:
                    logging.error(e)
                    transaction.savepoint_rollback(save_id)
                    return JsonResponse(reb('Process failed.', 1))
            return JsonResponse(reb('Reject Done.', 0))


class EditRoles(View):

    @method_decorator(Ssologin)
    @method_decorator(admin_check)
    def get(self, request, node_id):
        try:
            node = wfmodels.Node.objects.get(id=node_id)
        except wfmodels.Node.DoesNotExist as e:
            logging.error(e)
            return redirect('list_roles')
        user_id = request.GET.get('user_id')
        if user_id:
            try:
                wfmodels.Role.objects.get(id=user_id).delete()
            except Exception as e:
                logging.error(e)
                return redirect('roles_config', node_id=node_id)
        conn = get_redis_connection('default')
        users = conn.smembers('all_users')
        if not users:
            users = ldapsearch()
            conn.sadd('all_users', *users)
            conn.expire('all_users', 3600 * 24)
        else:
            users = set(u.decode() for u in users)
        current_users = wfmodels.Role.objects.filter(node_id=node)
        context = {
            'users': users,
            'node': node,
            'current_users': current_users
        }
        return render(request, 'role_edit.html', context)

    @method_decorator(Ssologin)
    @method_decorator(admin_check)
    def post(self, request, node_id):
        try:
            node = wfmodels.Node.objects.get(id=node_id)
        except wfmodels.Node.DoesNotExist as e:
            logging.error(e)
            return redirect('list_roles')
        user = request.POST.get('user_name_add')
        wfmodels.Role.objects.create(
            username=user,
            node_id=node
        )
        return redirect(request.get_full_path())


class RolesList(View):

    @method_decorator(Ssologin)
    @method_decorator(admin_check)
    def get(self, request):
        nodes = wfmodels.Node.objects.all().exclude(
            Q(name__contains='applied') | Q(name__in=['申请', '完成', '驳回']))
        for node in nodes:
            node.users = wfmodels.Role.objects.filter(node_id=node)
        context = {
            'nodes': nodes,
        }
        return render(request, 'role_list.html', context)


class TicketPending(View):

    @method_decorator(Ssologin)
    def get(self, request, page=1):
        user = request.session.get('user')
        roles = wfmodels.Role.objects.filter(username=user)
        q = request.GET.get('q')
        ticlist = list()
        for role in roles:
            ticl = wfmodels.Ticket.objects.filter(current_node=role.node_id)
            ticlist.extend(ticl)
        ticlist_new = wfmodels.Ticket.objects.filter(ticket_id__in=[i.ticket_id for i in ticlist]).order_by('-update_time')
        if q:
            ticlist = ticlist_new.filter(Q(ticket_id__contains=q) | Q(ticket_name__contains=q) | Q(applicant__contains=q)).order_by('-update_time')
        else:
            ticlist = ticlist_new
        pageinator_tool(ticlist, page)
        ticpages, pages = pageinator_tool(ticlist, page)
        context = {
            'allpage': ticpages,
            'pages': pages
        }
        return render(request, 'ticket_pending.html', context)


class TicketApproveDone(View):

    @method_decorator(Ssologin)
    def get(self, request, page=1):
        user = request.session.get('user')
        q = request.GET.get('q')
        ticlist = list()
        for i in wfmodels.Participation_info.objects.filter(participant='user'):
            ticlist.append(i)
        roles = wfmodels.Role.objects.filter(username=user)
        for role in roles:
            for i in wfmodels.Participation_info.objects.filter(node_id=role.node_id):
                ticlist.append(i.ticket_id)
        ticlist = list(set(ticlist))
        ticlist_new = wfmodels.Ticket.objects.filter(ticket_id__in=[i.ticket_id for i in ticlist]).order_by('-update_time')
        if q:
            ticlist = ticlist_new.filter(
                Q(ticket_id__contains=q) | Q(ticket_name__contains=q) | Q(applicant__contains=q)).order_by('-update_time')
        else:
            ticlist = ticlist_new
        pageinator_tool(ticlist, page)
        ticpages, pages = pageinator_tool(ticlist, page)
        context = {
            'allpage': ticpages,
            'pages': pages
        }
        return render(request, 'ticket_approve_done.html', context)


class FlowLists(View):

    @method_decorator(Ssologin)
    @method_decorator(admin_check)
    def get(self, request):
        ticket_types = wfmodels.TicketType.objects.all()
        context = {
            'ticket_types': ticket_types,
        }
        return render(request, 'flow_list.html', context)


class EditFlows(View):

    @method_decorator(Ssologin)
    @method_decorator(admin_check)
    def get(self, request, ticket_type_id):
        try:
            ticket_type = wfmodels.TicketType.objects.get(id=ticket_type_id)
        except wfmodels.TicketType.DoesNotExist as e:
            logging.error(e)
            return redirect('list_flows')
        current_node = wfmodels.Flow.objects.get(node_id__name='申请', flow_id=ticket_type)
        flows = list()
        while current_node.child_node_id:
            flows.append(current_node)
            current_node = wfmodels.Flow.objects.get(node_id=current_node.child_node_id, flow_id=ticket_type)

        nodes = wfmodels.Node.objects.all().exclude(name__in=['申请', '完成', '驳回'])
        context = {
            'flows': flows,
            'ticket_type': ticket_type,
            'nodes': nodes
        }
        return render(request, 'flow_edit.html', context)

    @method_decorator(Ssologin)
    @method_decorator(admin_check)
    def post(self, request, ticket_type_id):
        try:
            ticket_type = wfmodels.TicketType.objects.get(id=ticket_type_id)
        except wfmodels.TicketType.DoesNotExist as e:
            logging.error(e)
            return redirect('list_flows')
        current_node = wfmodels.Flow.objects.get(node_id__name='申请', flow_id=ticket_type)
        flows = list()
        while current_node.child_node_id:
            flows.append(current_node.node_id.name)
            current_node = wfmodels.Flow.objects.get(node_id=current_node.child_node_id, flow_id=ticket_type)
        nodes = request.POST.getlist('nodes')
        if flows != nodes:
            sid = transaction.savepoint()
            with transaction.atomic():
                try:
                    wfmodels.Flow.objects.filter(flow_id=ticket_type).delete()
                    for node in nodes:
                        node_index = nodes.index(node)
                        child_node_name = (nodes[node_index + 1] if node_index != len(nodes)-1 else '完成')
                        wfmodels.Flow.objects.create(
                            name=ticket_type.type_name + "_" + node,
                            flow_id=ticket_type,
                            node_id=wfmodels.Node.objects.get(name=node),
                            child_node_id=wfmodels.Node.objects.get(name=child_node_name)
                        )
                    wfmodels.Flow.objects.create(
                        name=ticket_type.type_name + "_完成",
                        flow_id=ticket_type,
                        node_id=wfmodels.Node.objects.get(name='完成'),
                        child_node_id=None
                    )
                    request.session['data'] = 'done.'
                except Exception as e:
                    logging.error(e)
                    request.session['data'] = 'System error.'
                    transaction.savepoint_rollback(sid)
        return redirect(request.get_full_path())


class NewFlows(View):

    @method_decorator(Ssologin)
    @method_decorator(admin_check)
    def get(self, request):
        nodes = wfmodels.Node.objects.all().exclude(name__in=['申请', '完成', '驳回'])
        context = dict()
        context['nodes'] = nodes
        return render(request, 'flow_new.html', context=context)

    @method_decorator(Ssologin)
    @method_decorator(admin_check)
    def post(self, request):
        ticket_type_name = request.POST.get('ticket_type_name')
        nodes = request.POST.getlist('nodes')
        context = dict()
        if not all([ticket_type_name, nodes]):
            context['data'] = '参数错误'
            return render(request, 'flow_new.html', context=context)
        if wfmodels.TicketType.objects.filter(type_name=ticket_type_name):
            context['data'] = '流程名称重复'
            return render(request, 'flow_new.html', context=context)
        sid = transaction.savepoint()
        with transaction.atomic():
            try:
                ticket_type = wfmodels.TicketType.objects.create(
                    type_name=ticket_type_name,
                    flow_id=uuid.uuid1()
                )
                for node in nodes:
                    node_index = nodes.index(node)
                    child_node_name = (nodes[node_index + 1] if node_index != len(nodes)-1 else '完成')
                    wfmodels.Flow.objects.create(
                        name=ticket_type_name + "_" + node,
                        flow_id=ticket_type,
                        node_id=wfmodels.Node.objects.get(name=node),
                        child_node_id=wfmodels.Node.objects.get(name=child_node_name)
                    )
                wfmodels.Flow.objects.create(
                    name=ticket_type_name + "_完成",
                    flow_id=ticket_type,
                    node_id=wfmodels.Node.objects.get(name='完成'),
                    child_node_id=None
                )
                request.session['data'] = 'done.'
                return redirect('list_flows')
            except Exception as e:
                logging.error(e)
                transaction.savepoint_rollback(sid)
                context['data'] = '添加失败'
                return render(request, 'flow_new.html', context=context)


class NewRoles(View):

    @method_decorator(Ssologin)
    @method_decorator(admin_check)
    def get(self, request):
        return render(request, 'role_new.html')

    @method_decorator(Ssologin)
    @method_decorator(admin_check)
    def post(self, request):
        role_name = request.POST.get('role_name')
        context = dict()
        if not role_name:
            context['data'] = '参数错误'
            return render(request, 'role_new.html', context=context)
        if wfmodels.Node.objects.filter(name=role_name):
            context['data'] = '流程名称重复'
            return render(request, 'role_new.html', context=context)
        sid = transaction.savepoint()
        with transaction.atomic():
            try:
                wfmodels.Node.objects.create(
                    name=role_name
                )
                request.session['data'] = 'done.'
                return redirect('list_roles')
            except wfmodels.Node.DoesNotExist as e:
                logging.error(e)
                transaction.savepoint_rollback(sid)
                context['data'] = '添加失败'
                return render(request, 'role_new.html', context=context)


class EditAdmins(View):

    @method_decorator(Ssologin)
    @method_decorator(admin_check)
    def get(self, request):
        context = {}
        deluser = request.GET.get('username')
        conn = get_redis_connection('default')
        users = conn.smembers('all_users')
        if not users:
            users = ldapsearch()
            conn.sadd('all_users', *users)
            conn.expire('all_users', 3600 * 24)
        else:
            users = set(u.decode() for u in users)
        context['users'] = users
        if deluser:
            conn.srem('admin_users', deluser)
            return redirect('admin_config')
        admins = conn.smembers('admin_users')
        admins = set(u.decode() for u in admins)
        context['admins'] = admins
        return render(request, 'admin_edit.html', context)

    @method_decorator(Ssologin)
    @method_decorator(admin_check)
    def post(self, request):
        user = request.POST.get('user_name_add')
        conn = get_redis_connection('default')
        if user:
            conn.sadd('admin_users', user)
        return redirect(request.get_full_path())


class AllTickets(View):

    @method_decorator(Ssologin)
    @method_decorator(admin_check)
    def get(self, request, page):
        q = request.GET.get('q')

        ticlist = wfmodels.Ticket.objects.all().order_by('-update_time')
        if q:
            ticlist = ticlist.filter(
                Q(ticket_id__contains=q) | Q(ticket_name__contains=q) | Q(applicant__contains=q)).order_by(
                '-update_time')
        ticpages, pages = pageinator_tool(ticlist, page)
        context = {
            'allpage': ticpages,
            'pages': pages
        }
        tickets = wfmodels.Ticket.objects.all().order_by('-update_time')
        context['tickets'] = tickets
        return render(request, 'allticket.html', context)


class Match(object):
    """
    总操作类, 状态机
    """
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def work(self):
        self.__class__ = Work

    # TODO: add others fsm


class Work(object):
    """
    子操作类
    """

    def __init__(self):
        super().__init__()

    def do(self, ticket_info):
        print("do:", ticket_info)
