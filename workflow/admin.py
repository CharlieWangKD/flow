from django.contrib import admin
from workflow.models import *


# Register your models here.
class TicketAdmin(admin.ModelAdmin):
    list_display = ['ticket_id', 'ticket_name', 'ticket_type', 'current_node', 'ticket_status', 'applicant', 'project']
    search_fields = ['ticket_id', 'ticket_name']


class TicketTypeAdmin(admin.ModelAdmin):
    list_display = ['type_name', 'flow_id']
    search_fields = ['type_name']


class RoleAdmin(admin.ModelAdmin):
    list_display = ['username', 'node_id']
    search_fields = ['username']


class NodeAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


class FlowAdmin(admin.ModelAdmin):
    list_display = ['name', 'flow_id', 'node_id', 'child_node_id']
    search_fields = ['name']


class Ticket_detailAdmin(admin.ModelAdmin):
    list_display = ['ticket_id', 'ticket_detail']
    search_fields = ['ticket_id']


class Participation_infoAdmin(admin.ModelAdmin):
    list_display = ['ticket_id', 'node_id', 'participant', 'suggestion', 'status']
    search_fields = ['ticket_id']


admin.site.register(Ticket, TicketAdmin)
admin.site.register(TicketType, TicketTypeAdmin)
admin.site.register(Role, RoleAdmin)
admin.site.register(Node, NodeAdmin)
admin.site.register(Flow, FlowAdmin)
admin.site.register(Ticket_detail, Ticket_detailAdmin)
admin.site.register(Participation_info, Participation_infoAdmin)

