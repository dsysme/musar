from django.contrib import admin
from payments import models
# Register your models here.


# class CompanyAdmin(admin.ModelAdmin):
#     list_display = ('cid', 'name')
#     search_field = ('name')
#
#
# class PaymentAdmin(admin.ModelAdmin):
#     list_display = ('buyer', 'seller', 'amount', 'dueDate')
#     search_field = ('buyer', 'seller', 'dueDate')


admin.site.register(models.Corporation)
admin.site.register(models.Payment)
