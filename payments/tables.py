from django_tables2 import tables, columns
from django_tables2.utils import A  # alias for Accessor
from payments.models import Payment, Corporation
from django.utils.translation import ugettext_lazy as _



class CorporationTable(tables.Table):
    cid = columns.TemplateColumn('{{ record.cid }}', verbose_name=_("Corporation ID"))
    days_late_average = columns.TemplateColumn('{{ record.lateness_average }}', verbose_name=_("Avg. of Extra Credit Days"))
    days_credit_average = columns.TemplateColumn('{{ record.credit_average }}', verbose_name=_("Avg. of Credit Days"))
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
            'days_late_average',
            'days_credit_average'
        )
        attrs = {"class": "table"}   

class MyCorporationTable(tables.Table):
    days_late_average = columns.TemplateColumn('{{ record.lateness_average }}', verbose_name=_("Avg. of Extra Credit Days"))
    days_credit_average = columns.TemplateColumn('{{ record.credit_average }}', verbose_name=_("Avg. of Credit Days"))
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
            'days_late_average',
            'days_credit_average'
        )
        attrs = {"class": "table"}   
  
        
class PaymentsTable(tables.Table):
    days_late = columns.TemplateColumn('{{ record.extra_credit_days }}', verbose_name=_("Avg. of Extra Credit Days"))
    days_credit = columns.TemplateColumn('{{ record.credit_days }}', verbose_name=_("Avg. of Credit Days"))
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
