from django.db import models

# Create your models here.


class BaseModel(models.Model):
    id = models.AutoField(primary_key=True)
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记')

    class Meta:
        abstract = True


class Ticket(BaseModel):
    ticket_name = models.CharField(max_length=50, verbose_name='工单名称', unique=True, null=False, db_index=True)
    ticket_id = models.CharField(max_length=50, verbose_name='工单id', unique=True, db_index=True)
    ticket_type = models.ForeignKey('TicketType', verbose_name='工单类型', db_index=True, on_delete=models.PROTECT)
    current_node = models.ForeignKey('Node', verbose_name='当前节点', on_delete=models.PROTECT)
    ticket_status = models.IntegerField(verbose_name='工单状态', choices=[
        (1, '申请'),
        (2, '处理中'),
        (3, '已处理'),
        (4, '已驳回')
    ])
    applicant = models.CharField(max_length=50, default='', verbose_name='申请人', db_index=True)

    class Meta:
        verbose_name = '工单表'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.ticket_name


class TicketType(BaseModel):
    type_name = models.CharField(max_length=50, verbose_name='工单类型', null=False, db_index=True)
    flow_id = models.CharField(max_length=50, verbose_name='流程id', null=False)

    class Meta:
        verbose_name = '工单类型表'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.type_name


class Role(BaseModel):
    username = models.CharField(max_length=50, verbose_name='关联用户名', null=False, db_index=True)
    node_id = models.ForeignKey('Node', on_delete=models.PROTECT, verbose_name='节点id')

    class Meta:
        unique_together = ("username", "node_id")
        verbose_name = '角色表'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.username


class Node(BaseModel):
    name = models.CharField(max_length=50, verbose_name='节点名称', null=False, db_index=True)
    # parent_node = models.ForeignKey("self", verbose_name='父节点', null=True, on_delete=models.PROTECT, blank=True)
    # child_node = models.ForeignKey("self", verbose_name='子节点', null=True, on_delete=models.PROTECT, blank=True)

    class Meta:
        verbose_name = '节点表'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class Flow(BaseModel):
    name = models.CharField(max_length=50, verbose_name='流程名称', null=False, db_index=True)
    flow_id = models.ForeignKey('TicketType', on_delete=models.PROTECT, verbose_name='审批流程')
    node_id = models.ForeignKey('Node', on_delete=models.PROTECT, verbose_name='节点id', related_name='node_id')
    child_node_id = models.ForeignKey('Node', on_delete=models.PROTECT, verbose_name='子节点id', related_name='child_node_id', blank=True, null=True)

    class Meta:
        verbose_name = '流程表'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class Ticket_detail(BaseModel):
    ticket_id = models.ForeignKey('Ticket', on_delete=models.PROTECT, verbose_name='工单id')
    ticket_detail = models.TextField(verbose_name='工单信息')

    class Meta:
        verbose_name = '工单详情表'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.ticket_id.ticket_name


class Participation_info(BaseModel):
    ticket_id = models.ForeignKey('Ticket', on_delete=models.PROTECT, verbose_name='工单id')
    node_id = models.ForeignKey('Node', on_delete=models.PROTECT, verbose_name='节点id')
    participant = models.CharField(max_length=50, verbose_name='处理人', null=False)
    suggestion = models.TextField(verbose_name='处理意见', blank=True)
    status = models.BooleanField(verbose_name='处理结果', default=True)

    class Meta:
        verbose_name = '处理情况表'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.ticket_id.ticket_name
