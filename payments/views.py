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
from payments.models import (
    Corporation, Payment, UserProfile, get_best_corporations, 
    get_worst_corporations 
)
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
    best = get_best_corporations()
    context['first'] = best[0]
    context['second'] = best[1]
    context['third'] = best[2]
    worst = get_worst_corporations()
    context['last'] = worst[0]
    context['last_prev'] = worst[1]
    context['last_prev_prev'] = worst[2]
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

    def __init__(self, user=None, *args, **kwargs):
        super(HomeView, self).__init__(*args, **kwargs)
        self.user = user

    def get_context_data(self, **kwargs):
        """ Adds tables of late and near due payments to the context
        """
        context = super(HomeView, self).get_context_data(**kwargs)

        # add overview payments
        table = PaymentsPartialTable(
            self.request.user.get_profile().overdue_payments
        )
        RequestConfig(self.request, paginate={"per_page": 3}).configure(table) 
        context['table'] = table
        	
        # add payments due in 6 days
        table_1 = PaymentsPartialTable(
            self.request.user.get_profile().neardue_payments
        )
        RequestConfig(self.request, paginate={"per_page": 3}).configure(table_1)
        context['table_neardue_payments'] = table_1
        return context

    #  This is how you decorate class see:
    #  https://docs.djangoproject.com/en/1.5/topics/class-based-views/intro/
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(HomeView, self).dispatch(*args, **kwargs)


@login_required
def statistics(a_request, username):
	try:
		# consider taking username from the request
		user = User.objects.get(username = username)
		profile = user.get_profile()
		assert user != None
		assert profile != None
		return render(a_request, 'payments/statistics.html', 
			{'user': user, 'user_profile': profile}
		)
	except User.DoesNotExist:
		return HttpResponse("Invalid username")

@login_required
def settings(a_request, username):
    return render(a_request, 'payments/settings.html', {'username': username})
   
@login_required 
def compare_view(a_request, corporation):
    c = get_object_or_404(Corporation, cid=corporation)
    assert c != None
    user = User.objects.get(username=a_request.user.username)
    profile = user.get_profile()
    return render(a_request, 'payments/compare_corporation.html', 
    	{'user': user, 
    	'corporation': c, 
        'rating': c.rating,
    	'user_profile': profile}
    )


# NO login_required    
def corporation_details(a_request, corporation):
    c = get_object_or_404(Corporation, cid=corporation)
    assert c != None
    return render(a_request, 'payments/corporation_details.html', 
        { 'corporation': c }
    )


# NO login_required    
def corporation_list(a_request):
    model = Corporation
    template_name = 'payments/corporations_list.html'
    table_class = CorporationTable
    table_pagination = {"per_page": 10}


# login_required
class MyCorporationsList(SingleTableView):
    model = Corporation
    template_name = 'payments/my_corporations.html'
    table_class = MyCorporationTable
    table_pagination = {"per_page": 10}
	
    def get_queryset(self):
		# filter for current user
		return UserProfile.objects.get(user=self.request.user).corporations.all()

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
    table_pagination = {"per_page": 10}
    table_data = Corporation.objects.all()
    
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
    
    def get_queryset(self):
        if self.request.method == 'POST':
            corporation = self.request.POST.get('corporation')
            payments_list = [payment for payment in self.request.user.payment_set.all() if payment.coporation__eq(corporation)]
        else:
            payments_list = [payment for payment in self.request.user.payment_set.all()]
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
#  	assert False
# 	stripped_csv_data = (item.strip() for item in csv_data.split())
 	payments = PaymentCsvModel.import_data(csv_data.split('\r\n'))
	for csv_model in payments:
		corporation = Corporation.objects.get(cid=csv_model.corporation)
		assert corporation != None
		
		p = Payment(
			corporation=corporation, 
    		owner=a_request.user,
    		amount=csv_model.amount,
    		title=csv_model.title,
    		due_date=csv_model.due_date,
    		supply_date=csv_model.supply_date,
    		order_date=csv_model.order_date,
    		pay_date=csv_model.pay_date
		)
		
		p.save()
	return HttpResponseRedirect(reverse_lazy('payments',
        kwargs={'username': username})
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


# @login_required
# def add_payments_file(request, username, filename):
#     return HttpResponseRedirect(
#         reverse_lazy('payments'), kwargs={'username': username})


def search(a_request):
    search_term = a_request.GET['search_term'.encode('utf-8')].strip()
    # TODO check if match exist and redirect only if one match found
    return HttpResponseRedirect(
        reverse_lazy('corporation', kwargs={'corporation': search_term})
    )


def corporation_detail(a_request, corporation):
    obj = get_object_or_404(Corporation, name__icontains=corporation)
    assert obj != None
    return render(a_request, 'payments/company.html', {'corporation': obj})
