from django_tables2 import tables, columns
from django_tables2.utils import A  # alias for Accessor
from payments.models import Payment, Corporation



class CorporationTable(tables.Table):
    days_late_average = columns.TemplateColumn('{{ record.lateness_average }}')
    days_credit_average = columns.TemplateColumn('{{ record.credit_average }}')
    name = columns.LinkColumn('corporation_details', kwargs={'corporation': A('cid')}, verbose_name='corporation') #, kwargs={'corporation': A('name')}
#
    class Meta:
        model = Corporation
  
        exclude = (
            'url',
            'email',
            'slug_name'
        )    
        sequence = (
            'cid',
            'name',
            'days_late_average',
            'days_credit_average',
        )
        attrs = {"class": "table"}   

class MyCorporationTable(tables.Table):
    days_late_average = columns.TemplateColumn('{{ record.lateness_average }}')
    days_credit_average = columns.TemplateColumn('{{ record.credit_average }}')
    name = columns.LinkColumn('compare_corporation', kwargs={'corporation': A('cid')}, verbose_name='corporation') #, kwargs={'corporation': A('name')}
#
    class Meta:
        model = Corporation
  
        exclude = (
            'url',
            'email',
            'slug_name'
        )    
        sequence = (
            'cid',
            'name',
            'days_late_average',
            'days_credit_average',
        )
        attrs = {"class": "table"}   
        
class PaymentsTable(tables.Table):
    days_late = columns.TemplateColumn('{{ record.extra_credit_days }}')
    days_credit = columns.TemplateColumn('{{ record.credit_days }}')
    class Meta:
        model = Payment
        exclude = ('owner', 'created_at')
        order_date = columns.DateColumn()
        supply_date = columns.DateColumn()
        due_date = columns.DateColumn()
        pay_date = columns.DateColumn()
        sequence = (
            'id',
            'corporation',
            'title',
            'amount',
            'order_date',
            'supply_date',
            'due_date',
            'pay_date',
            'days_late',
            'days_credit',
        )
        attrs = {"class": "table"}


class PaymentsPartialTable(tables.Table):

    action = columns.TemplateColumn(
        accessor='corporation.email',
        verbose_name='Send Reminder',
        template_name='payments/send_reminder.html',
        orderable=False)

    last_reminder = columns.Column(verbose_name='Last Reminder',)

    class Meta:
        model = Payment
        due_date = columns.DateColumn()
        exclude = (
            'owner',
            'created_at',
            'id',
            'order_date',
            'supply_date',
            'pay_date'
        )
        sequence = (
            'corporation',
            'title',
            'amount',
            'due_date',
            'last_reminder',
            'action',
        )
        attrs = {"class": "table"}
