from django.contrib import admin
from django.http.request import HttpRequest
from django.http.response import HttpResponse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from django.db.models.functions import Concat
from django.db.models import Value
from .models import GHPUser, Account, Piece, Ledger
from django.contrib import messages
from django.utils.translation import ngettext
import csv
from django.http import HttpResponse

# Register your models here.


class CurrentUserFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _("Current User")

    # Parameter for the filter that will be used in the URL query.
    parameter_name = "current"

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return [
            ("true", _("Yes")),
            ("false", _("No")),
        ]

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        # Compare the requested value (either 'true' or 'false')
        # to decide how to filter the queryset.
        if self.value() == "true":
            return queryset.filter(
                Q(current_student=True) | Q(current_staff=True) | Q(current_admin=True))
        if self.value() == "false":
            return queryset.filter(
                Q(current_student=False) & Q(current_staff=False) & Q(current_admin=False))


class BalanceFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _("Balance")

    # Parameter for the filter that will be used in the URL query.
    parameter_name = "balancerange"

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return [
            ("positive", _("Positive")),
            ("negative", _("Negative")),
            ("zero", _("Zero")),
            ("10_plus", _("Bal > $10")),
            ("10_to_0", _("$10 > Bal > $0")),
            ("0_to_-25", _("$0 > Bal >= -$25")),
            ("-25_to_-125", _("-$25 > Bal >= -$125")),
            ("-25_to_any", _("-$25 >= Bal")),
            ("-125_to_any", _("-$125 >= Bal")),

        ]

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        # Compare the requested value (
        # '10_plus' or '10_to_0' or 'positive' or 'zero' or 'negative' 
        # or '-25_to_0' or '-125_to_-25' or '-125_to_any')
        # to decide how to filter the queryset.
        if self.value() == "10_plus":
            return queryset.filter(balance__gt=10)
        if self.value() == "10_to_0":
            return queryset.filter(balance__lte=10, balance__gt=0)
        if self.value() == "positive":
            return queryset.filter(balance__gt=0)
        if self.value() == "zero":
            return queryset.filter(balance=0)
        if self.value() == "negative":
            return queryset.filter(balance__lt=0)
        if self.value() == "0_to_-25":
            return queryset.filter(balance__lt=0, balance__gte=-25)
        if self.value() == "-25_to_any":
            return queryset.filter(balance__lte=-25)
        if self.value() == "-25_to_-125":
            return queryset.filter(balance__lt=-25, balance__gte=-125)
        if self.value() == "-125_to_any":
            return queryset.filter(balance__lte=-125)

class AmountFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _("Amount")

    # Parameter for the filter that will be used in the URL query.
    parameter_name = "amountrange"

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return [
            ("positive", _("Positive (credit)")),
            ("negative", _("Negative (debit)")),
            ("zero", _("Zero")),
            ("100_plus", _("Amt > $100")),
            ("50_plus", _("Amt > $50")),
            ("10_plus", _("Amt > $10")),
            ("10_to_0", _("$10 > Amt > $0")),
            ("0_to_-50", _("$0 > Amt > -$50")),
            ("-50_to_any", _("-$50 >= Amt")),
        ]

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        # Compare the requested value ('positive', 'negative', 'zero', '100_plus', 
        # '50_plus', '10_plus', '10_to_0', '0_to_-50', '-50_to_any')
        # to decide how to filter the queryset.

        if self.value() == "100_plus":
            return queryset.filter(amount__gt=100)
        if self.value() == "50_plus":
            return queryset.filter(amount__gt=50)
        if self.value() == "10_plus":
            return queryset.filter(amount__gt=10)
        if self.value() == "positive":
            return queryset.filter(amount__gt=0)
        if self.value() == "zero":
            return queryset.filter(amount=0)
        if self.value() == "negative":
            return queryset.filter(amount__lt=0)
        if self.value() == "10_to_0":
            return queryset.filter(amount__lte=10, amount__gt=0)
        if self.value() == "0_to_-50":
            return queryset.filter(amount__lt=0, amount__gte=-50)
        if self.value() == "-50_to_any":
            return queryset.filter(amount__lte=-50)
        
class PriceFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _("Price")

    # Parameter for the filter that will be used in the URL query.
    parameter_name = "pricerange"

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return [
            ("100_plus", _("Price > $100")),
            ("100_to_50", _("$100 > Price >= $50")),
            ("50_to_0", _("$50 > Price > $0")),
            ("50_to_25", _("$50 > Price >= $25")),
            ("25_to_0", _("$25 > Price > $0")),
            ("25_to_10", _("$25 > Price >= $10")),
            ("10_to_0", _("$10 > Amt > $0")),
            ("1", _("$1")),
        ]

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        # Compare the requested value ('100_plus', '100_to_50', '50_to_0', '50_to_25',
        # '25_to_0', '25_to_10', '10_to_0', '1')
        # to decide how to filter the queryset.

        if self.value() == "100_plus":
            return queryset.filter(price__gt=100)
        if self.value() == "100_to_50":
            return queryset.filter(price__lte=100, price__gt=50)
        if self.value() == "50_to_0":
            return queryset.filter(price__lt=50, price__gt=0)
        if self.value() == "50_to_25":
            return queryset.filter(price__lte=50, price__gt=25)
        if self.value() == "25_to_0":
            return queryset.filter(price__lt=25, price__gt=0)
        if self.value() == "25_to_10":
            return queryset.filter(price__lte=25, price__gt=10)
        if self.value() == "10_to_0":
            return queryset.filter(price__lte=10, price__gt=0)
        if self.value() == "1":
            return queryset.filter(price=1)
        
class LengthORWidthFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _("Length OR Width")

    # Parameter for the filter that will be used in the URL query.
    parameter_name = "len_or_width_range"

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return [
            ("15_plus", _("L, W >= 15")),
            ("15_to_10", _("15 > L,W >= 10")),
            ("10_to_5", _("10 > L,W > 5")),
            ("5_to_0", _("5 > L,W > 0")),
            ("0.5", _("L,W = 0.5")),
        ]

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        # Compare the requested value (15_plus, 15_to_10, 10_to_5, 5_to_0, 0.5)
        # to decide how to filter the queryset.

        if self.value() == "15_plus":
            return queryset.filter(Q(length__gte=15) | Q(width__gte=15))
        if self.value() == "15_to_10":
            return queryset.filter(Q(length__lt=15, length__gte=10) | Q(width__lt=15, width__gte=10))
        if self.value() == "10_to_5":
            return queryset.filter(Q(length__lt=10, length__gt=5) | Q(width__lt=10, width__gt=5))
        if self.value() == "5_to_0":
            return queryset.filter(Q(length__lt=5, length__gt=0) | Q(width__lt=5, width__gt=0))
        if self.value() == "0.5":
            return queryset.filter(Q(length=0.5) | Q(width=0.5))

class LengthANDWidthFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _("Length AND Width")

    # Parameter for the filter that will be used in the URL query.
    parameter_name = "len_and_width_range"

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return [
            ("15_plus", _("L, W >= 15")),
            ("15_to_10", _("15 > L,W >= 10")),
            ("10_to_5", _("10 > L,W > 5")),
            ("5_to_0", _("5 > L,W > 0")),
            ("0.5", _("L,W = 0.5")),
        ]
    
    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        # Compare the requested value (15_plus, 15_to_10, 10_to_5, 5_to_0, 0.5)
        # to decide how to filter the queryset.
    
        if self.value() == "15_plus":
            return queryset.filter(length__gte=15, width__gte=15)
        if self.value() == "15_to_10":
            return queryset.filter(length__lt=15, length__gte=10, width__lt=15, width__gte=10)
        if self.value() == "10_to_5":
            return queryset.filter(length__lt=10, length__gt=5, width__lt=10, width__gt=5)
        if self.value() == "5_to_0":
            return queryset.filter(length__lt=5, length__gt=0, width__lt=5, width__gt=0)
        if self.value() == "0.5":
            return queryset.filter(length=0.5, width=0.5)

class HeightFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _("Height")

    # Parameter for the filter that will be used in the URL query.
    parameter_name = "heightrange"

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return [
            ("15_plus", _("H >= 15")),
            ("15_to_10", _("15 > H >= 10")),
            ("10_to_5", _("10 > H> 5")),
            ("5_to_0", _("5 > H > 0")),
            ("0.5", _("H = 0.5")),
        ]
    
    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        # Compare the requested value (15_plus, 15_to_10, 10_to_5, 5_to_0, 0.5)
        # to decide how to filter the queryset.

        if self.value() == "15_plus":
            return queryset.filter(Q(height__gte=15))
        if self.value() == "15_to_10":
            return queryset.filter(height__lt=15, height__gte=10)
        if self.value() == "10_to_5":
            return queryset.filter(height__lt=10, height__gt=5)
        if self.value() == "5_to_0":
            return queryset.filter(height__lt=5, height__gt=0)
        if self.value() == "0.5":
            return queryset.filter(height=0.5)
        
class CurrentUserFilterFromOther(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _("Current User")

    # Parameter for the filter that will be used in the URL query.
    parameter_name = "current"

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return [
            ("true", _("Yes")),
            ("false", _("No")),
        ]

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        # Compare the requested value (either 'true' or 'false')
        # to decide how to filter the queryset.
        if self.value() == "true":
            return queryset.filter(
                Q(ghp_user__current_student=True) | Q(ghp_user__current_staff=True) | Q(ghp_user__current_admin=True))
        if self.value() == "false":
            return queryset.filter(
                Q(ghp_user__current_student=False) & Q(ghp_user__current_staff=False) & Q(ghp_user__current_admin=False))


# class ExportCsvMixin:
    # from: 
    # https://books.agiliq.com/projects/django-admin-cookbook/en/latest/export.html
    @admin.action(description="Export selected objects as csv")
    def export_as_csv(self, request, queryset):

        meta = self.model._meta
        field_names = [field.name for field in meta.fields]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)

        writer.writerow(field_names)
        for obj in queryset:
            row = writer.writerow([getattr(obj, field) for field in field_names])

        return response

    export_as_csv.short_description = "Export Selected"




class GHPUserAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'email', 'phone_number',
                     'current_student', 'current_staff', 'current_admin', 
                     'last_measure_date', 'consent', 'consent_date', 'current']

    list_filter = ['current_student', 'current_staff', 'current_admin', CurrentUserFilter]

    search_fields = ['first_name', 'last_name', 'email', 'phone_number']

    ordering = ['last_name', 'first_name', 'email',  'last_measure_date', 'consent_date']

    actions = ['make_students', 'make_staff', 'make_admins', 'make_not_current', 'export_as_csv']

    list_display_links = ["first_name", "last_name", 'email', 'phone_number']

    @admin.display(description='Current', boolean=True)
    def current(self, obj):
        return obj.current_student or obj.current_staff or obj.current_admin

    @admin.action(description="Mark selected users as current students")
    def make_students(self, request, queryset):
        updated = queryset.update(current_student=True)
        self.message_user(
            request,
            ngettext(
                "%d user was successfully marked as student.",
                "%d users were successfully marked as students.",
                updated,
            )
            % updated,
            messages.SUCCESS,
        )

    @admin.action(description="Mark selected users as current staff")
    def make_staff(self, request, queryset):
        updated = queryset.update(current_staff=True)
        self.message_user(
            request,
            ngettext(
                "%d user was successfully marked as staff.",
                "%d users were successfully marked as staff.",
                updated,
            )
            % updated,
            messages.SUCCESS,
        )
    
    @admin.action(description="Mark selected users as current admins")
    def make_admins(self, request, queryset):
        updated = queryset.update(current_admin=True)
        self.message_user(
            request,
            ngettext(
                "%d user was successfully marked as admin.",
                "%d users were successfully marked as admins.",
                updated,
            )
            % updated,
            messages.SUCCESS,
        )
    
    @admin.action(description="Mark selected users as not current students, staff, nor admins")
    def make_not_current(self, request, queryset):
        updated = queryset.update(current_student=False, current_staff=False, current_admin=False)
        self.message_user(
            request,
            ngettext(
                "%d user was successfully marked as NOT current.",
                "%d users were successfully marked as NOT current.",
                updated,
            )
            % updated,
            messages.SUCCESS,
        )
    
    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


class AccountAdmin(admin.ModelAdmin):

    fieldsets = [
        (
            None,
            {   "classes": ["pretty"],
                "fields": ['ghp_user', 'balance_link', 'piece_link', 'ledger_credit_link', 'last_update']
            }
        ),

    ]


    list_display = ['name', 'email',  'balance', 'last_update', "ghp_user", 'balance_link', 'piece_link', 'ledger_credit_link']

    list_filter = [ BalanceFilter, 'last_update', CurrentUserFilterFromOther]

    search_fields = ['ghp_user__first_name', 'ghp_user__last_name', 'ghp_user__email']

    ordering = ['balance', 'last_update']

    readonly_fields = ["ghp_user", 'balance', 'balance_link', 'piece_link', 'ledger_credit_link', 'last_update']

    list_display_links = ['name', 'email', "ghp_user", 'balance', 'last_update']

    actions = ['export_as_csv']


    @admin.display(ordering="ghp_user__last_name")
    def name(self, obj):
        return str(obj.ghp_user.first_name) + ' ' + str(obj.ghp_user.last_name)


    @admin.display(ordering="ghp_user__email")
    def email(self, obj):
        return str(obj.ghp_user.email)

    @admin.display(description="balance (link to ledger)")
    def balance_link(self, obj):
        balance = obj.balance
        url = (
            reverse("admin:measure_ledger_changelist")
            + "?"
            + urlencode({"ghp_user__user_ptr__exact": f"{obj.ghp_user.id}"})
        )
        return format_html('<a href="{}">{}</a>', url, balance)
    
    @admin.display(description="User Pieces (link to pieces)")
    def piece_link(self, obj):
        url = (
            reverse("admin:measure_piece_changelist")
            + "?"
            + urlencode({"ghp_user__user_ptr__exact": f"{obj.ghp_user.id}"})
        )
        return format_html('<a href="{}">User Measuring Log</a>', url)


    @admin.display(description="Add Credit")
    def ledger_credit_link(self, obj):
        """ This is a custom column that links to the add credit page, 
        and passes the account.ghp_user as a parameter"""
        url = (
            reverse("admin:measure_ledger_add")
            + "?"
            + urlencode({"ghp_user__id": f"{obj.ghp_user.id}"})
        )
        return format_html('<a href="{}">Add Credit</a>', url)



    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    # def add_view(self, request: HttpRequest, form_url: str = ..., extra_context: None = ...) -> HttpResponse:
    #     return super().add_view(request, form_url, extra_context)

    # def formfield_for_foreignkey(self, db_field, request, **kwargs):
    #     if db_field.name == "car":
    #         kwargs["queryset"] = Car.objects.filter(owner=request.user)
    #     return super(MyModelAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)


class PieceAdmin(admin.ModelAdmin):
    fieldsets = [
        (
            None,
            {
                "fields": ['name', 'email', 'length', 'width', 'height', 'size', 'price', 'bisque_temp', 'glaze_temp', 'date', 'image'],
            },
        ),
        # (
        #     "Advanced options",
        #     {
        #         "classes": ["collapse"],
        #         "fields": ["registration_required", "template_name"],
        #     },
        # ),
    ]

    list_display = ['ghp_user', 'ghp_user_piece_id', 'glaze_temp', 'date', 'price',
                    'length', 'width', 'height', 'size', 'bisque_temp', 'email', 'image',  ]

    list_display_links = ['ghp_user', 'ghp_user_piece_id']

    @admin.display(ordering="ghp_user__last_name")
    def name(self, obj):
        return str(obj.ghp_user.first_name) + ' ' + str(obj.ghp_user.last_name)


    @admin.display(ordering="ghp_user__email")
    def email(self, obj):
        return str(obj.ghp_user.email)

    readonly_fields = ['ghp_user_piece_id', 'date', 'ghp_user', 'name', 
                       'email', 'length', 'width', 'height', 'size', 
                       'price','bisque_temp', ]

    list_filter = ['glaze_temp', 'bisque_temp', 'date', CurrentUserFilterFromOther,
                   PriceFilter, LengthORWidthFilter, LengthANDWidthFilter, HeightFilter,
                   'ghp_user__current_student', 'ghp_user__current_staff', 'ghp_user__current_admin']
    
    search_fields = ['ghp_user__first_name', 'ghp_user__last_name', 'ghp_user__email']
    
    ordering = ['-date', 'ghp_user__last_name', 'ghp_user__first_name']

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions





class LedgerAdmin(admin.ModelAdmin):

    list_display = [ 'transaction_type', 'date', 'amount', 'ghp_user', 'piece', 
                    'note', 'transaction_id']
    
    list_filter = ['transaction_type', 'date', AmountFilter, CurrentUserFilterFromOther, 'ghp_user__current_student', 'ghp_user__current_staff', 'ghp_user__current_admin']
    
    search_fields = ['ghp_user__first_name', 'ghp_user__last_name', 'ghp_user__email', 
                     'transaction_type', 'date', 'note']
    
    ordering = ['-date', 'ghp_user__last_name', 'ghp_user__first_name']

    readonly_fields = ['transaction_id', 'date']

    autocomplete_fields = ['ghp_user', 'piece',] 

    fieldsets = [
        (
            None,
            {   "classes": ["pretty"],
                "fields": ['ghp_user', 'amount', 'transaction_type', 'piece', 'note'],
            },
        ),
    ]


    # changes all fields to be read only when editing an existing object
    def get_readonly_fields(self, request, obj=None):
        # from
        # https://stackoverflow.com/questions/4343535/django-admin-make-a-field-read-only-when-modifying-obj-but-required-when-adding
        if obj: # editing an existing object
            # All model fields as read_only
            return self.readonly_fields + list(tuple([item.name for item in obj._meta.fields if item.name != "note"]))
        return self.readonly_fields


    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions
    
#     def get_changeform_initial_data(self, request):
#         print("request:", request)
#         if request.
#         return {"ghp_user": request.id}
# #        return {"amount": 50}
    
    # def get_formset_kwargs(self, request, obj, inline, prefix):
    #     return {
    #         **super().get_formset_kwargs(request, obj, inline, prefix),
    #         "form_kwargs": {"request": request},
    #     }

    # def get_changeform_initial_data(self, request):
    #     print("request:", request)
    #     return {"ghp_user": request.id}


from django.contrib import admin
from django.shortcuts import redirect
from django.shortcuts import render

from django.contrib import admin

@admin.site.admin_view
def my_custom_view(request):
    # perform some custom action
    # ...
    return render(request, 'my_custom_template.html')




admin.site.register(GHPUser, GHPUserAdmin)
admin.site.register(Account, AccountAdmin)
admin.site.register(Piece, PieceAdmin)
admin.site.register(Ledger, LedgerAdmin)
