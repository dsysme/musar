from datetime import timedelta, date, datetime

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import models
# from django.utils.datetime_safe import datetime, date
from django.utils.translation import ugettext_lazy as _
from django.db.models.signals import post_save
from django.template.defaultfilters import slugify

import numpy
from payments.managers import (
    ExtraCreditManager, CreditManager,OverduePaymentsManager, 
    OverduePaymentsManager, NearduePaymentsManager, CorporationStatisticsManager
)

MAX_LEGAL_CREDIT_DAYS=45


def regulation_due_date(supply_date):
    """ Due date might be latter than regulations premits. In such case,
        the latest date regulation allow is returned. 
    """
    max_legal_credit_date = supply_date + \
        timedelta(days=get_max_legal_credit_days(supply_date))
        
    return max_legal_credit_date



class Corporation(models.Model):
    """ Corporation profile """
    cid = models.CharField(
        primary_key=True,
        max_length=200,
        unique=True,
        help_text="Corporation's ID",
        verbose_name=_("Corporation ID")
    )

    name = models.CharField(max_length=200, unique=True, verbose_name=_("Name"))
    slug_name = models.CharField(max_length=200, unique=True, null=True)
    url = models.URLField(null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    
    # Managers
    # use Corporation.objects.with_statistics() to get Corporation 
    # with statistic data this is unecessarly expensive unless you need the 
    # corporation score with necessitate fetch for all objects 
    objects = CorporationStatisticsManager()

    def __unicode__(self):
        return self.name
    
def get_max_legal_credit_days(supply_date):
    # TODO: implement the real computation which is based on supply_date shotef+
    return MAX_LEGAL_CREDIT_DAYS


class Payment(models.Model):
    """ Holds the details of a pass or future payment
        Based on these details, the statistics of payments ethics are calculated
    """

    corporation = models.ForeignKey(
        Corporation,
        verbose_name=_('Corporation ID'),
        db_index = True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Input date'),
        help_text=_('Created At'),
    )
    owner = models.ForeignKey(
        User,
        verbose_name=_('Created By'),
        db_index = True,
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_('Amount'),
    )
    title = models.CharField(
        max_length=400,
        verbose_name=_('Description'),
        blank=True
    )
    due_date = models.DateField(
        verbose_name=_('Due Date'),
        null=True,
        blank=True
    )
    supply_date = models.DateField(
        verbose_name=_('Supply Date'),
    )
    order_date = models.DateField(
        default=date.today(),
        verbose_name=_('Order Date'),
        null=True,
        blank=True
    )
    pay_date = models.DateField(
        verbose_name=_('Pay Date'),
        null=True,
        blank=True
    )
    
    objects = models.Manager() # The default manager.

     # needed for efficiency when filtering by corporation
    late_payments = ExtraCreditManager()
    credit_payments = CreditManager()
    
    # needed for efficiency when filtering by user
    overdue_payments = OverduePaymentsManager()
    neardue_payments = NearduePaymentsManager()
    
    def __unicode__(self):
        return self.title + " " + str(self.id)\
            + self.owner.username + " " + self.corporation.name \
            + str(self.get_extra_credit_days()) +  " " \
            + str(self.get_credit_days()) 

    def get_absolute_url(self):
        return reverse('add_payments', kwargs={'pk': self.pk})

#     def __unicode__(self):
#         return self.title + self.corporation.name + self.owner.username
    
    #TODO does this should be a class method?
    @classmethod
    def create(cls, corporation, owner, amount, title, due_date, supply_date, pay_date):
        c = Corporation.objects.get(name=corporation)
        if c is None:
            raise ValueError

        payment = cls(
            corporation=c,
            owner=owner,
            amount=amount,
            title=title,
            due_date=due_date,
            supply_date=supply_date,
            pay_date=pay_date,
        )

    def get_extra_credit_days(self):
        # TODO: make sure date is not in future
        effective_due_date = min(self.due_date, 
            regulation_due_date(self.supply_date)
        )
        if (self.pay_date == None):
            # ToDo: add test for this if
            return max(0, (date.today() - effective_due_date).days)
        return max((self.pay_date - effective_due_date).days, 0)
    
    def get_credit_days(self):
        if (self.pay_date == None):
            # ToDo: add test for this if
            return max(0, (date.today() - self.supply_date).days)
        return max(0, (self.pay_date - self.supply_date).days)
    
    class Meta:
        verbose_name = _("Payment")
        verbose_name_plural = _("Payments")


class SupplierUser(User):
    
    def get_overdue_payments(self, corporation_cid=None):
        if (corporation_cid is not None):
            return Payment.overdue_payments.filter(owner=self)\
                .filter(corporation__cid=corporation_cid)
        return Payment.overdue_payments.filter(owner=self)

    def get_neardue_payments(self, corporation_cid=None):
        if (corporation_cid is not None):
            return Payment.neardue_payments.filter(owner=self)\
                .filter(corporation__cid=corporation_cid)
        return Payment.neardue_payments.filter(owner=self)
    
    def get_extra_credit_count(self, corporation_cid=None):
        if (corporation_cid is not None):
            return Payment.late_payments.filter(owner=self)\
                .filter(corporation__cid=corporation_cid).count()
        return Payment.late_payments.filter(owner=self).count()
    
    def get_payments_count(self, corporation_cid=None):
        if (corporation_cid is not None):
            return Payment.objects.filter(owner=self)\
                .filter(corporation__cid=corporation_cid).count()
        return Payment.objects.filter(owner=self).count()
    
    def get_total_extra_credit_days(self, corporation_cid=None):
        late_payments = []
        if (corporation_cid is not None):
            late_payments = Payment.late_payments.filter(owner=self)\
                .filter(corporation__cid=corporation_cid)
        else:
            late_payments = Payment.late_payments.filter(owner=self)
        result = 0
        for payment in late_payments:
            result += payment.get_extra_credit_days()
        return result
    
    def get_avg_extra_credit(self, corporation_cid=None):
        result = 0
        if (corporation_cid is not None):
            count = self.get_payments_count(corporation_cid)
            if count > 0:
                result = self.get_total_extra_credit_days(corporation_cid)/self.get_payments_count(corporation_cid)
        else:
            count = self.get_payments_count()
            if count > 0:
                result = self.get_total_extra_credit_days()/self.get_payments_count()
        return result
    
    def get_total_credit_days(self, corporation_cid=None):
        credit_payments = []
        if (corporation_cid is not None):
            credit_payments = Payment.credit_payments.filter(owner=self)\
                .filter(corporation__cid=corporation_cid)
        else:
            credit_payments = Payment.credit_payments.filter(owner=self)
        result = 0
        for payment in credit_payments:
            result += payment.get_credit_days()
        return result
    
    def get_avg_credit(self, corporation_cid=None):
        result = 0
        if (corporation_cid is not None):
            count = self.get_payments_count(corporation_cid)
            if count > 0:
                result = self.get_total_credit_days(corporation_cid)/self.get_payments_count(corporation_cid)
        else:
            count = self.get_payments_count()
            if count > 0:
                result = self.get_total_credit_days()/self.get_payments_count()
        return result
    
    def get_payments_with_moral_data(self, corporation_cid=None):
        result = []
        if (corporation_cid is not None):
            result = Payment.objects.filter(owner__id=self.id).filter(corporation__cid=corporation_cid)
        else: 
            result = Payment.objects.filter(owner__id=self.id)
        for payment in result:
            payment.extra_credit_days = payment.get_extra_credit_days()
            payment.credit_days = payment.get_credit_days()
        return result
    
    class Meta:
        proxy = True        
