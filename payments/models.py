from datetime import timedelta, date, datetime

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import models
# from django.utils.datetime_safe import datetime, date
from django.utils.translation import ugettext_lazy as _
from django.db.models.signals import post_save
from django.template.defaultfilters import slugify
from django.db.models import Q
from django.db.models import F
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


def get_extra_credit_days(supply_date, due_date, pay_date):
    # TODO: make sure date is not in future
    effective_due_date = min(due_date, 
            regulation_due_date(supply_date)
    )
    if (pay_date == None):
        # ToDo: add test for this if
        return max(0, (date.today() - effective_due_date).days)
    return max((pay_date - effective_due_date).days, 0)

def get_credit_days(supply_date, pay_date):
        if (pay_date == None):
            # ToDo: add test for this if
            return max(0, (date.today() - supply_date).days)
        return max(0, (pay_date - supply_date).days)

    

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

    def __unicode__(self):
        return self.name
    
    @property
    def payments_count(self):
        return self.payment_set.count()
    
    def payments_late_days(self):
        payments = self.payment_set.filter(Q(due_date__lt=date.today()) & Q(pay_date__isnull=True) | Q(due_date__lt=F('pay_date'))).values('due_date', 'pay_date', 'supply_date')
        payments_extra_credit_days_list = \
            [get_extra_credit_days(payment['supply_date'], payment['due_date'], payment['pay_date']) for payment in payments]
        return payments_extra_credit_days_list
    
#     @property
#     def late_payments_count(self):
#         late_payments = list(payment for payment in self.payment_set.all() \
#             if payment.extra_credit_days > 0)
#         return len(late_payments_set)
    
    @property
    def lateness_average(self):
        list = self.payments_late_days()
        result = numpy.mean(list)
        if len(list)==0:
            return 0
        return numpy.sum(list)/self.payment_set.count()
    
    @property
    def lateness_sum(self):
        list = self.payments_late_days()
        return sum(list)
    
    def payments_credit_days(self):
        days = 0
        payments = self.payment_set.filter(Q(supply_date__lt=F('pay_date'))).values('pay_date', 'supply_date')
        payments_credit_days_list = [get_credit_days(payment['supply_date'], payment['pay_date']) for payment in payments] 
        return payments_credit_days_list                

    @property
    def credit_average(self):
        list = self.payments_credit_days()
        if len(list)==0:
            return 0
        return numpy.sum(list)/self.payment_set.count()
    
    @property
    def credit_sum(self):
        list = self.payments_credit_days()
        return sum(list)

    @property
    def score(self):
        score = self.credit_sum + 2 * self.lateness_sum
        return score
    
    @property
    def rating(self):
        # TODO might be performance issue here http://stackoverflow.com/questions/16322513/django-order-by-a-property
        list = sorted(Corporation.objects.all(), key=lambda m: m.score)
        index = list.index(self)
        return index


def get_best_corporations():
    list = sorted(Corporation.objects.all(), key=lambda m: m.score)
    return list[0:3]


def get_worst_corporations():
    list = sorted(Corporation.objects.all(), key=lambda m: m.score, reverse=True)
    return list[0:3]


class PaymentType(object):
    """indication if this is payment to or payment by"""
    IN = 1
    OUT = 2

    choices = (
        (IN, 'In'),
        (OUT, 'Out'),
    )

def get_max_legal_credit_days(supply_date):
    # TODO: implement the real computation which is based on supply_date shotef+
    return MAX_LEGAL_CREDIT_DAYS


class Payment(models.Model):
    """ Holds the details of a pass or future payment
        Based on these details the statistics of payments etique are gathered
    """

    corporation = models.ForeignKey(
        Corporation,
#         related_name='corporation_payments',
        verbose_name=_('Corporation ID'),
        db_index = True,
        # help_text=_('The paying corporation'),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Input date'),
        help_text=_('Created At'),
    )
    owner = models.ForeignKey(
        User,
#         related_name='payments',
        verbose_name=_('Created By'),
        db_index = True,
        # help_text=_('Who is getting this payment'),
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_('Amount'),
        # help_text=_('How much money should be paid'),
    )
    title = models.CharField(
        max_length=400,
        verbose_name=_('Description'),
        blank=True
        # help_text=_('Short description of the payment. Who? What for?'),
    )
    due_date = models.DateField(
        verbose_name=_('Due Date'),
        null=True,
        blank=True
        # help_text=_('The date the payment is due'),
    )
    supply_date = models.DateField(
        verbose_name=_('Supply Date'),
        # help_text=_('The date the goods or services where delivared'),
    )
    order_date = models.DateField(
        default=date.today(),
        verbose_name=_('Order Date'),
        # help_text=_('The date the supply was ordered'),
        null=True,
        blank=True
    )
    pay_date = models.DateField(
        verbose_name=_('Pay Date'),
        # help_text=_('The date the payment was paid'),
        null=True,
        blank=True
    )
    
    def save(self, *args, **kwargs):
        # add the corporation to the owners corporations list
        profile, is_created = UserProfile.objects.get_or_create(user=self.owner)
        assert profile is not None
        corporation = Corporation.objects.get(cid=self.corporation.cid)
        assert corporation is not None
        if corporation not in profile.corporations.all():
            profile.corporations.add(
                Corporation.objects.get(cid=self.corporation.cid)
            )
        super(Payment, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.title + " " + self.owner.username + " " + self.corporation.name + " " + str(self.extra_credit_days) + " " + str(self.supply_date) +  " " + str(self.due_date) + " " + str(self.pay_date) 

    def get_absolute_url(self):
        return reverse('add_payments', kwargs={'pk': self.pk})

    @classmethod
    def create(cls, corporation, owner, amount, title, due_date, supply_date):
        c = Corporation.objects.get(name=corporation)
        if c is None:
            raise ValueError
        payment = cls(
            corporation=c,
            owner=owner,
            amount=amount,
            title=title,
            due_date=due_date,
            supply_date=supply_date
        )

    @property
    def extra_credit_days(self):
        # TODO: make sure date is not in future
        effective_due_date = min(self.due_date, 
            regulation_due_date(self.supply_date)
        )
        if (self.pay_date == None):
            # ToDo: add test for this if
            return max(0, (date.today() - effective_due_date).days)
        return max((self.pay_date - effective_due_date).days, 0)
    
    @property
    def credit_days(self):
        if (self.pay_date == None):
            # ToDo: add test for this if
            return max(0, (date.today() - self.supply_date).days)
        return max(0, (self.pay_date - self.supply_date).days)

    class Meta:
        verbose_name = _("Payment")
        verbose_name_plural = _("Payments")
        

class UserProfile(models.Model):  
    user = models.OneToOneField(User) 
    neardue_days = models.DecimalField(default=6, decimal_places=0, max_digits=2)
    corporations = models.ManyToManyField(Corporation, null=True)

    def __str__(self):  
          return "%s's profile" % self.user  

    def create_user_profile(sender, instance, created, **kwargs):  
        if created:  
           profile, created = UserProfile.objects.get_or_create(user=instance)
    
    @property
    def overdue_payments(self):
        late_payments = [
            payment for payment in self.user.payment_set.filter(Q(due_date__lt=date.today()) & Q(pay_date__isnull=True))
        ]
        return late_payments
         
    @property
    def neardue_payments(self):
        neardue_payments = [
            payment for payment in self.user.payment_set.filter(Q(due_date__lt=date.today() + timedelta(days=6)) & Q(pay_date__isnull=True))
        ]

        return neardue_payments

    @property       
    def payments_count_by_corporation(self, corporation):
        payments_list = [payment for payment in self.user.payment_set.filter(corporation_eq=corporation)]
        return len(payments_list)
           
    @property
    def payments_count(self):
        return self.user.payment_set.count()
    
    @property
    def total_late_days(self):
        days = 0
        for payment in self.user.payment_set.all():
            days += payment.extra_credit_days
        return days
    
    @property
    def late_payments_count(self):
        late_payments = [payment for payment in self.user.payment_set.all() \
            if payment.extra_credit_days > 0]
        return len(late_payments)
    
    @property
    def lateness_average(self):
        if self.payments_count > 0:
            return self.total_late_days/self.payments_count
        return 0
    
    @property
    def total_credit_days(self):
        days = 0
        for payment in self.user.payment_set.all():
            days += payment.credit_days
        return days
        
    @property
    def credit_average(self):
        if self.payments_count > 0:
            return self.total_credit_days/self.payments_count
        return 0

    post_save.connect(create_user_profile, sender=User) 
        
        

