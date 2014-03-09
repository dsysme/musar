from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse_lazy
from django.http import request
from django.shortcuts import render_to_response
from django.http.response import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
#from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
#from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, FormView
from django_tables2 import SingleTableView, RequestConfig
from payments.forms import AddPaymentForm, LoadFileForm
from payments.models import Corporation, Payment, SupplierUser

from django.template import RequestContext
import logging
from payments.csv_models import PaymentCsvModel
from django.http import HttpResponseNotFound
from django.utils.translation import ugettext_lazy as _
from payments.tables import ( 
    PaymentsTable, PaymentsPartialTable, CorporationTable, MyCorporationTable
)


# Get an instance of a logger
logger = logging.getLogger(__name__)
# from django.utils.datetime_safe import datetime

# Create your views here.


def index(a_request):
    context = RequestContext(a_request)
    corporations = sorted(Corporation.objects.with_statistics(), 
        key=lambda t: t.rating)
    context['best'] = []
    context['worst'] = []
    if len(corporations) > 3:
        if (c.rating > 0 for c in corporations[0:3]):
            context['best'] = corporations[0:3]
        if (c.rating > 0 for c in corporations[-3:]):
            context['worst'] = corporations[-3:]
    return render(a_request, 'payments/index.html', context_instance=context)


def register(a_request):
    return render(a_request, 'payments/register.html')


@login_required
def after_login(a_request):
    username = a_request.user.username
    return HttpResponseRedirect(
        reverse_lazy('home', kwargs={'username': username}))


class HomeView(SingleTableView):

    model = Payment
    template_name = 'payments/home.html'
    table_class = PaymentsPartialTable

    def get_context_data(self, **kwargs):
        """ Adds tables of late and near due payments to the context
        """
        context = super(HomeView, self).get_context_data(**kwargs)
        u = SupplierUser.objects.get(pk=self.request.user.pk)

        # add overview (late) payments
        table = PaymentsPartialTable(u.get_overdue_payments())
#         RequestConfig(self.request, paginate={"per_page": 3}).configure(table) 
        context['table'] = table
        	
        # add payments due in 6 days
        table_1 = PaymentsPartialTable(u.get_neardue_payments())
#         RequestConfig(self.request, paginate={"per_page": 3}).configure(table_1)
        context['table_neardue_payments'] = table_1
        return context

    #  This is how you decorate class see:
    #  https://docs.djangoproject.com/en/1.5/topics/class-based-views/intro/
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(HomeView, self).dispatch(*args, **kwargs)


@login_required
def statistics(a_request, username):
    #TODO consider applying DRY for this view and compare_view
    try:
        user = SupplierUser.objects.get(pk=a_request.user.pk)
        assert user != None
    except User.DoesNotExist:
        return HttpResponse("Invalid username")

    return render(a_request, 'payments/statistics.html', 
        {'user': user, 
        'count': user.get_payments_count(),
        'late_count': user.get_extra_credit_count(),
        'extra_credit_avg': user.get_avg_extra_credit(),
        'credit_avg': user.get_avg_credit()}
    )

@login_required
def settings(a_request, username):
    return render(a_request, 'payments/settings.html', {'username': username})
   
@login_required 
def compare_view(a_request, corporation):
    #TODO consider applying DRY for this view and statitics
    all_corporations = Corporation.objects.with_statistics()
    c = next((c for c in all_corporations if c.cid == corporation), None)
    assert c != None
    user = SupplierUser.objects.get(pk=a_request.user.pk)

    return render(a_request, 'payments/compare_corporation.html', {
        'user': user, 
        'corporation': c,
        'count': user.get_payments_count(c.cid),
        'late_count': user.get_extra_credit_count(c.cid),
        'extra_credit_avg': user.get_avg_extra_credit(c.cid),
        'credit_avg': user.get_avg_credit(c.cid)
    })


# login_required
class MyCorporationsList(SingleTableView):
    model = Corporation
    template_name = 'payments/my_corporations.html'
    table_class = MyCorporationTable
    table_pagination = {"per_page": 10}
	
    
    def get_table_data(self):
	   # filter for current user
       my_corporation = Payment.objects.filter(owner=self.request.user).values('corporation')
       my_corporation_cid = [cid['corporation'] for cid in my_corporation]
       all_corporations = Corporation.objects.with_statistics()
       my_corporation_with_stat = [corporation for \
            corporation in all_corporations\
            if corporation.cid in my_corporation_cid]
       return my_corporation_with_stat

    # This is how you decorate class see:
    # https://docs.djangoproject.com/en/1.5/topics/class-based-views/intro/
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
		return super(MyCorporationsList, self).dispatch(*args, **kwargs)


# login NOT required
class CorporationsList(SingleTableView):
    model = Corporation
    template_name = 'payments/table.html'
    table_class = CorporationTable
    table_pagination = {"per_page": 5}
    table_data = Corporation.objects.with_statistics()
    
#     def get_quearyset(self):
#         all_corporations = Corporation.objects.with_statistics()
#         assert False
#         return all_corporations
     
    def get_context_data(self, **kwargs):
        """ Add title
        """
        context = super(CorporationsList, self).get_context_data(**kwargs)
        context['title'] = _("Corporations List")
        return context
	

# login_required
class PaymentsList(SingleTableView):
    model = Payment
    template_name = 'payments/payments.html'
    table_class = PaymentsTable
#     table_data = self.request.user.payment_set.all()
    
    def get_table_data(self):

        user = SupplierUser.objects.get(pk=self.request.user.pk)
        if self.request.method == 'POST':
            #TODO where do we use this
            corporation = self.request.POST.get('corporation')
            payments_list = user.get_payments_with_moral_data(corporation)
        else:
            payments_list = user.get_payments_with_moral_data()
    	return payments_list

    # This is how you decorate class see:
    # https://docs.djangoproject.com/en/1.5/topics/class-based-views/intro/
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(PaymentsList, self).dispatch(*args, **kwargs)


def load_payments_from_file_view(a_request, username):
    # TODO skip empty lines in input file
    if a_request.method == 'POST':
        payments = []
        form = LoadFileForm(a_request.POST, a_request.FILES)
        if form.is_valid():
        	csv_file = a_request.FILES.get('file')
        	csv_text = ''.join(csv_file.readlines())
         	payments = PaymentCsvModel.import_from_file(csv_file)
         	return render(
                a_request,
                'payments/add_payments.html',
                {'table': PaymentsTable(payments),
                 'csv_text': csv_text,
                 'csv_file_type': str(type(csv_file)),
                 }
            )
        else:
            raise ValueError("Form not valid")
    else:
        form = LoadFileForm(a_request)
        return render_to_response(
            'payments/loadpaymentsfile_form.html',
            {'form': form},
            context_instance=RequestContext(a_request),
        )

def save_payments_list_view(a_request, username):
    if a_request.method != 'POST':
		return HttpResponseNotFound('<h1>No Page Here</h1>')

    csv_data = a_request.POST.get('csv_text')
    payments_csv = PaymentCsvModel.import_data(csv_data.split('\r\n'))
    payments = []
    for csv_model in payments_csv:
		corporation = Corporation.objects.get(cid=csv_model.corporation)
		assert corporation != None #TODO handle corporation not exist
		
		payments.append(Payment(
			corporation=corporation, 
    		owner=a_request.user,
    		amount=csv_model.amount,
    		title=csv_model.title,
    		due_date=csv_model.due_date,
    		supply_date=csv_model.supply_date,
    		order_date=csv_model.order_date,
    		pay_date=csv_model.pay_date)
		)
		
	# P.A. bulk_create a number of caveats like not calling custom save
    # read https://docs.djangoproject.com/en/dev/ref/models/querysets/ for 
    # more details on bulk_create caveats
    Payment.objects.bulk_create(payments, batch_size=500)
    
    return HttpResponseRedirect(reverse_lazy('payments',
        kwargs={'username': username})
    )

# NO login_required    
def corporation_details(a_request, corporation):
    all_corporations = Corporation.objects.with_statistics()
    c = next((c for c in all_corporations if c.cid == corporation), None)
    assert c != None
    return render(a_request, 'payments/corporation_details.html', 
        { 'corporation': c }
    )

# login_required
class PaymentCreate(CreateView):

    model = Payment
    form_class = AddPaymentForm
    fields = (
        'corporation',
        'title',
        'amount',
        'due_date',
        'supply_date',
        'pay_date'
    )

    def form_valid(self, form):
    	# set the hidden field to current user
        form.instance.created_by = self.request.user
        form.instance.owner = self.request.user
        return super(PaymentCreate, self).form_valid(form)

    def get_success_url(self):
        return reverse_lazy('payments', kwargs={'username': self.request.user})

    """This is how you decorate class see:
       https://docs.djangoproject.com/en/1.5/topics/class-based-views/intro/"""
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(PaymentCreate, self).dispatch(*args, **kwargs)



