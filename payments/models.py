from datetime import timedelta, date, datetime

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import models
# from django.utils.datetime_safe import datetime, date
from django.utils.translation import ugettext_lazy as _
from django.db.models.signals import post_save
from django.template.defaultfilters import slugify
from django.db.models import Q, F, Sum
import numpy
import json

MAX_LEGAL_CREDIT_DAYS=45

def dthandler(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    else:
        return json.JSONEncoder().default(obj)


class ShareOption(object):
    """Sharing information policies"""
    NONE = 1
    RESTRICTED = 2
    ALL = 3

    choices = (
        (NONE, 'Share None'),
        (RESTRICTED, 'Share Only With Companies Involved'),
        (ALL, 'Share All'),
    )

def regulation_due_date(supply_date):
    """ Due date might be latter than regulations premits. In such case,
        the latest date regulation allow is returned. 
    """
    max_legal_credit_date = supply_date + \
        timedelta(days=get_max_legal_credit_days(supply_date))
        
    return max_legal_credit_date


# def get_extra_credit_days(supply_date, due_date, pay_date):
#     # TODO: make sure date is not in future
#     effective_due_date = min(due_date, 
#             regulation_due_date(supply_date)
#     )
#     if (pay_date == None):
#         # ToDo: add test for this if
#         return max(0, (date.today() - effective_due_date).days)
#     return max((pay_date - effective_due_date).days, 0)
# 
# def get_credit_days(supply_date, pay_date):
#         if (pay_date == None):
#             # ToDo: add test for this if
#             return max(0, (date.today() - supply_date).days)
#         return max(0, (pay_date - supply_date).days)
#     

def overdue_payments(user):
    # return payments that are late and unpaid
    late_payments = [
        payment for payment in user.payment_set.filter(
                Q(due_date__lt=date.today()) & Q(pay_date__isnull=True)
        )
    ]
    return late_payments

          
def neardue_payments(user):
    # return payments that are due in 6 days at most 
    neardue_payments = [
        payment for payment in user.payment_set.filter(
            Q(due_date__lt=date.today() + timedelta(days=6)) 
            & Q(pay_date__isnull=True)
        )
    ]
    return neardue_payments


class ExtraCreditManager(models.Manager):
    def get_query_set(self):
        return Payment.filter(
            Q(pay_date__isnull=False) 
            & Q(due_date__lt=F('pay_date'))
            | Q(pay_date__isnull=True)
        )
             
#         from django.db import connection
#         cursor = connection.cursor()
#         # TODO cover case when supply date is future or not given
#         # TODO make sure due_date is legal
#         # fetch late payments
#         cursor.execute("""
#             SELECT *
#             FROM payments_payment 
#             WHERE pay_date IS NULL OR pay_date IS NOT NULL AND due_date < pay_date
#             ORDER BY due_date DESC""")
#             
# 
#         # calculate for each late payment, the extra_credit_days and return
#         # as list
#         result_list = []
#         for payment in cursor.fetchall():
#             payment.extra_credit_days = Payment.calc_extra_credit_days(
#                         payment['supply_date'], 
#                         payment['due_date'], 
#                         payment['pay_date']
#             )
#             result_list.append(payment)
#         
#         return result_list


class CreditManager(models.Manager):
    
    def get_query_set(self):
        return Payment.filter(
            Q(pay_date__isnull=False) & Q(supply_date__lt=F('pay_date'))
            | Q(pay_date__isnull=True) & Q(supply_date__lt=date.today())
        )
             
#         from django.db import connection
#         cursor = connection.cursor()
#         cursor.execute("""
#             SELECT (*)
#             FROM payments_payment 
#             WHERE pay_date IS NOT NULL AND supply_date < pay_date
#                 OR pay_date IS NULL AND supply_date < CURDATE()
#             ORDER BY supply_date DESC""")
#             
#         # calculate for each payment unpaid or paid after supply, the 
#         # credit_days and return as list
#         result_list = []
#         for payment in cursor.fetchall():
#             payment.extra_credit_days = Payment.calc_credit_days(
#                 payment['supply_date'], 
#                 payment['pay_date']
#             )
#             result_list.append(payment)
#     
#         return result_list
 
class StatisticsManager(models.Manager):
    
    # P.A.: the result is not a QuerySet, therefor cannot be filtered or
    # applied any other QuerySet methods.
    # This manager purpose is to rate all corporation at O(1) db operations
    # instead of the trivial model use which will result in db access and
    # rating all corporation for each access to one corporation rating  
    def get_query_set(self):
        corporations = Corporation.objects.all()
        scores = {}
        
        # calculate and add score
        for c in corporations:
            count_late_days = 0
            count_credit_days = 0
            
            # filter late/with credit payments for corporation c
            late_payments = Payment.late_payments.filter(corporation=c.cid)
            credit_payments = Payment.credit_payments.filter(corporation=c.cid)
            
            # count all the payments associated with corporation c
            total_payments = Payment.filter(corporation=c.cid).count()
            
            # count the late days over all payments for corporation c
            for payment in late_payments:
                assert payment.extra_credit_days != None and payment.extra_credit_days > 0
                count_late_days = count_late_days + payment.extra_credit_days 
            
            c.extra_credit_days = count_late_days
            c.avg_extra_credit_days = count_late_days/total_payments
            
            # count the credit days over all payments for corporation c
            for payment in credit_payments:
                assert payment.credit_days != None and payment.credit_days > 0
                count_credit_days = count_credit_days + payment.credit_days
                
            c.credit_days = count_credit_days
            c.avg_credit_days = count_credit_days/total_payments
            
            # The more late/credit days the higher the score is
            c.score = count_credit_days + 2 * count_late_days
            scores.add(score)
        
        # calculate and add rating
        
        # since scores is a set, each score is unique and the position of a 
        # corporation's score in the in the soretd score list gives indication
        # on the corporation's moral ethics compare to other corporations 
        sorted_scores = sorted(scores)
        for c in corporations:
            c.rating = sorted_scores.index(c.score)
        
        return corporations
            
    
# TODO consult if the method should be properties 
# http://stackoverflow.com/questions/17429159/idiomatic-python-property-or-method
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
    objects = models.Manager() # The default manager.
    with_statistics = StatisticsManager()

    def __unicode__(self):
        return self.name
    
#     @property
#     def payments_count(self):
#         """ returns the count of payments associated with this corporation
#         """
#         return self.payment_set.count()
#     
#     # don't make this a property if you do, the rating will not be shown in view
#     def total_extra_credit_days(self):
#         """ return total number of late days associated with this corporation
#         """
#         result = Payments.late_payments.filter(corporation=self.cid)\
#             .aggregate(Sum('extra_credit_days'))
#             
#         return result['extra_credit_days__sum']
#     
#     @property
#     def extra_credit_sum(self):
#         return self.total_extra_credit_days()
# 
#     @property
#     def lateness_average(self):
#         return self.extra_credit_sum/self.payments_count
#     
#     # don't make this a property if you do, the rating will not be shown in view
#     def total_credit_days(self):
#         """ return total number of late days associated with this corporation
#         """
#         result = Payments.credit_payments.filter(corporation=self.cid)\
#             .aggregate(Sum('credit_days'))
#             
#         return result['credit_days__sum'] 
# 
#     @property
#     def credit_sum(self):
#         return self.total_credit_days()
# 
#     @property
#     def credit_average(self):
#         return self.credit_sum/self.payments_count
#  

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
    late_payments = ExtraCreditManager()
    credit_payments = CreditManager()
    
    def __unicode__(self):
        return self.title + " " \
            + self.owner.username + " " + self.corporation.name \
            + " " + str(self.calc_extra_credit_days) + " " \
            + str(self.supply_date) +  " " + str(self.due_date) \
            + " " + str(self.pay_date) 

    def get_absolute_url(self):
        return reverse('add_payments', kwargs={'pk': self.pk})

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

    @classmethod
    def _extra_credit_days(self):
        # TODO: make sure date is not in future
        effective_due_date = min(self.due_date, 
            regulation_due_date(self.supply_date)
        )
        if (pay_date == None):
            # ToDo: add test for this if
            return max(0, (date.today() - effective_due_date).days)
        return max((self.pay_date - effective_due_date).days, 0)
    
    extra_credit_days = property(_extra_credit_days)
    
    @classmethod
    def _credit_days(self):
        if (pay_date == None):
            # ToDo: add test for this if
            return max(0, (date.today() - self.supply_date).days)
        return max(0, (self.pay_date - self.supply_date).days)
    
    credit_days = property(_credit_days)

    class Meta:
        verbose_name = _("Payment")
        verbose_name_plural = _("Payments")
        

#