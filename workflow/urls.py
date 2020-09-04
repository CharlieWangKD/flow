"""workflow URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.views.generic import RedirectView
from workflow import views

urlpatterns = [
    url(r'^$', RedirectView.as_view(pattern_name="apply", permanent=False)),
    url(r'^login\/?$', views.login, name="login"),
    url(r'^logout\/?$', views.logout, name="logout"),
    url(r'^workflow/apply\/?$', views.CreateTestTicket.as_view(), name="apply"),  # 申请工单
    url(r'^workflow/myticket/(?P<ticstatus>\d)/(?P<page>\d+)\/?$', views.Myticket.as_view(), name="list_myticket"),   # 查看我申请的工单
    url(r'^workflow/ticket_detail/(?P<ticket_id>.+)\/?$', views.TicketDetail.as_view(), name="ticket_detail"),    # 工单详情(不需要引导)
    url(r'^workflow/ticket_detail_approve/(?P<ticket_id>.+)\/?$', views.TicketDetailApprove.as_view(), name="ticket_detail_approve"),  # 工单审批(不需要引导)
    url(r'^workflow/ticket_update$', views.TicketUpdate.as_view(), name="ticket_update"),  # ajax审批接口(不需要引导)
    url(r'^workflow/roles_config/(?P<node_id>.+)\/?$', views.EditRoles.as_view(), name="roles_config"),  # 节点配置(不需要引导)
    url(r'^workflow/roles$', views.RolesList.as_view(), name="list_roles"),  # 节点列表
    url(r'^workflow/ticket_pending/(?:(?P<page>\d+)/)?\/?$', views.TicketPending.as_view(), name="ticket_pending"),  # 我的待审批工单
    # url(r'^workflow/ticket_pending\/?$', RedirectView.as_view(url='/api/v1/workflow/ticket_pending/1', permanent=False)),  # 我的待审批工单
    url(r'^workflow/ticket_approved/(?:(?P<page>\d+)/)?\/?$', views.TicketApproveDone.as_view(), name="ticket_approved"),  # 我的已审批工单
    url(r'^workflow/flows$', views.FlowLists.as_view(), name="list_flows"),  # 流程列表
    url(r'^workflow/flows_config/(?P<ticket_type_id>.+)\/?$', views.EditFlows.as_view(), name="flows_config"),  # 流程配置(不需要引导)
    url(r'^workflow/new_flow\/?$', views.NewFlows.as_view(), name="new_flow"),  # 新建工单流程
    url(r'^workflow/new_role\/?$', views.NewRoles.as_view(), name="new_role"),  # 新建角色
    url(r'^sys\/?$', RedirectView.as_view(pattern_name="list_roles", permanent=False)),
    url(r'^workflow/admin_config$', views.EditAdmins.as_view(), name="admin_config"),  # 管理员配置
    url(r'^workflow/all/(?P<page>\d+)\/?$', views.AllTickets.as_view(), name='all_ticket'),  # 后台所有工单
]
