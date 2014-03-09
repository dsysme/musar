from datetime import timedelta, date
from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q, F


# manager for getting payments with extra_credit
class ExtraCreditManager(models.Manager):
    def get_query_set(self):
        from payments.models import Payment
        return Payment.objects.filter(
            Q(pay_date__isnull=False) 
            & Q(due_date__lt=F('pay_date'))
            & Q(due_date__lt=date.today())
            | Q(pay_date__isnull=True)
            & Q(due_date__lt=date.today())
        )
        
        
# manager for getting payments with credit
class CreditManager(models.Manager):
    
    def get_query_set(self):
        from payments.models import Payment
        return Payment.objects.filter(
            Q(pay_date__isnull=False) & Q(supply_date__lt=F('pay_date'))
            | Q(pay_date__isnull=True) & Q(supply_date__lt=date.today())
        )
        
 
# manager for getting unpaid late payments, designed to be used with 
# compbination with user's filter   
class OverduePaymentsManager(models.Manager):
    
    def get_query_set(self):
        # return payments that are unpaid for witch due date passed
        from payments.models import Payment
        return Payment.objects.filter(
            Q(due_date__lt=date.today()) 
            & Q(pay_date__isnull=True)
        )
                              

# manager for getting neardue payments, designed to be used with 
# compbination with user's filter                                 
class NearduePaymentsManager(models.Manager):

    def get_query_set(self):
        # return payments that are due in 6 days at most 
        from payments.models import Payment
        return Payment.objects.filter(
            Q(due_date__lt=date.today()+timedelta(days=6)) 
            & Q(due_date__gte=date.today())
            & Q(pay_date__isnull=True)
        )


# manager for getting corporation's statistics
class CorporationStatisticsManager(models.Manager):
    
    # P.A.: the result is not a QuerySet, therefor cannot be filtered or
    # applied any other QuerySet methods.
    # This manager purpose is to rate all corporation at O(1) db operations
    # instead of the trivial model use which will result in db access and
    # rating all corporation for each access to one corporation rating  
    def with_statistics(self):
        from payments.models import Corporation
        from payments.models import Payment
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
            total_payments = Payment.objects.filter(corporation=c.cid).count()
            c.payments_count = total_payments
            
            # count the late days over all payments for corporation c
            for payment in late_payments:
                assert payment.get_extra_credit_days() != None \
                    and payment.get_extra_credit_days() > 0
                count_late_days = count_late_days \
                    + payment.get_extra_credit_days()
            
            c.extra_credit_days = count_late_days
            c.avg_extra_credit_days = 0
            if (total_payments > 0):
                c.avg_extra_credit_days = count_late_days/total_payments
            
            # count the credit days over all payments for corporation c
            for payment in credit_payments:
                assert payment.get_credit_days() != None \
                    and payment.get_credit_days() > 0
                count_credit_days = count_credit_days + \
                    payment.get_credit_days()
                
            c.credit_days = count_credit_days
            c.avg_credit_days = 0
            if (total_payments > 0):
                c.avg_credit_days = count_credit_days/total_payments
            
            # The more late/credit days the higher the score is
            c.score = count_credit_days + 2 * count_late_days
            scores.update({str(c.score): c.score})
        
        # calculate and add rating
        
        # since scores is a set, each score is unique and the position of a 
        # corporation's score in the in the soretd score list gives indication
        # on the corporation's moral ethics compare to other corporations 
        sorted_scores = sorted(scores.values())
        for c in corporations:
            c.rating = sorted_scores.index(c.score) + 1
        
        corporations = sorted(corporations, key=lambda c: c.rating)
        return corporations
            

          

