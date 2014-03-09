from django_tables2 import tables, columns
from django_tables2.utils import A  # alias for Accessor
from payments.models import Payment, Corporation
from django.utils.translation import ugettext_lazy as _



class CorporationTable(tables.Table):
    cid = columns.TemplateColumn('{{ record.cid }}', verbose_name=_("Corporation ID"))
    avg_extra_credit_days = columns.TemplateColumn('{{ record.avg_extra_credit_days }}', verbose_name=_("Avg. of Extra Credit Days"))
    avg_credit_days = columns.TemplateColumn('{{ record.avg_credit_days }}', verbose_name=_("Avg. of Credit Days"))
    rating = columns.TemplateColumn('{{ record.rating }}', verbose_name=_("Rating"))
    name = columns.LinkColumn('corporation_details', kwargs={'corporation': A('cid')}, verbose_name=_('corporation'))#, kwargs={'corporation': A('name')}
    
    class Meta:
        model = Corporation
  
        exclude = (
            'url',
            'email',
            'slug_name',
        )    
        sequence = (
            'cid',
            'name',
            'rating',
            'avg_extra_credit_days',
            'avg_credit_days'
        )
        attrs = {"class": "table"}   

class MyCorporationTable(tables.Table):
#     avg_extra_credit_days = columns.TemplateColumn('{{ record.avg_extra_credit_days }}', verbose_name=_("Avg. of Extra Credit Days"))
#     avg_credit_days = columns.TemplateColumn('{{ record.avg_credit_days }}', verbose_name=_("Avg. of Credit Days"))
    rating = columns.TemplateColumn('{{ record.rating }}', verbose_name=_("Rating"))
    name = columns.LinkColumn('compare_corporation', kwargs={'corporation': A('cid')}, verbose_name=_('corporation'))

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
            'rating',
#             'avg_extra_credit_days',
#             'avg_credit_days'
        )
        attrs = {"class": "table"}   
  
        
class PaymentsTable(tables.Table):
    extra_credit_days = columns.TemplateColumn('{{ record.extra_credit_days }}', verbose_name=_("Extra Credit Days"))
    credit_days = columns.TemplateColumn('{{ record.credit_days }}', verbose_name=_("Credit Days"))
    corporation = columns.LinkColumn('compare_corporation', kwargs={'corporation': A('corporation.cid')}, verbose_name=_('corporation'))

    class Meta:
        model = Payment
        exclude = ('id','owner', 'created_at', 'order_date')
        sequence = (
            'corporation',
            'title',
            'amount',
            'supply_date',
            'due_date',
            'pay_date',
            'extra_credit_days',
            'credit_days',
        )
        attrs = {"class": "table"}


class PaymentsPartialTable(tables.Table):

    action = columns.TemplateColumn(
        accessor='corporation.email',
        verbose_name=_('Send Reminder'),
        template_name='payments/send_reminder.html',
        orderable=False)

    last_reminder = columns.Column(verbose_name=_('Last Reminder'),)

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
