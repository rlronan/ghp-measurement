from django.contrib import admin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from django.db.models.functions import Concat
from django.db.models import Value
from .models import GHPUser, Account, Piece, Ledger
# Register your models here.


class CurrentUserFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _("current anything")

    # Parameter for the filter that will be used in the URL query.
    parameter_name = "true"

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
        # Compare the requested value (either '80s' or '90s')
        # to decide how to filter the queryset.
        if self.value() == "true":
            return queryset.filter(Q(current_student=True) | Q(current_staff=True) | Q(current_admin=True))
        if self.value() == "false":
            return queryset.filter(Q(current_student=False) & Q(current_staff=False) & Q(current_admin=False))



class BalanceFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _("Balance")

    # Parameter for the filter that will be used in the URL query.
    parameter_name = "range"

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return [
            ("25_plus", _("> $25")),
            ("50_to_0", _("$50 -- $0")),
            ("positive", _("Positive")),
            ("zero"), _("Zero"),
            ("negative", _("Negative")),
            ("-50_to_0", _("-$50 -- $0")),
            ("-125_to_-50", _("-$125 -- $50")),
            ("-125_to_any", _("< -$125")),

        ]

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        # Compare the requested value (either '80s' or '90s')
        # to decide how to filter the queryset.
        if self.value() == "true":
            return queryset.filter(Q(current_student=True) | Q(current_staff=True) | Q(current_admin=True))
        if self.value() == "false":
            return queryset.filter(Q(current_student=False) & Q(current_staff=False) & Q(current_admin=False))












@admin.action(description="Mark selected users as current students")
def make_students(modeladmin, request, queryset):
    queryset.update(current_student=True)

# @admin.action(description="Mark selected users as current teachers")
# def make_teachers(modeladmin, request, queryset):
#     queryset.update(current_teacher=True)

@admin.action(description="Mark selected users as current staff")
def make_staff(modeladmin, request, queryset):
    queryset.update(current_staff=True)

@admin.action(description="Mark selected users as current admins")
def make_admins(modeladmin, request, queryset):
    queryset.update(current_admin=True)

@admin.action(description="Mark selected users as not current students, staff, nor admins")
def make_not_current(modeladmin, request, queryset):
    queryset.update(current_student=False, current_staff=False, current_admin=False)



class GHPUserAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'email', 
                    'phone_number', 'current_student',
                      'current_staff', 'current_admin', 'last_measure_date', 'consent', 'consent_date', 'current']
    list_filter = ['current_student', 'current_staff', 'current_admin', CurrentUserFilter]
    search_fields = ['first_name', 'last_name', 'email', 'phone_number']
    ordering = ['last_name', 'first_name', 'email',  'last_measure_date', 'consent_date']
    actions = [make_students, make_staff, make_admins, make_not_current]
    list_display_links = ["first_name", "last_name", 'email', 'phone_number']
    @admin.display(description='Current', boolean=True)
    def current(self, obj):
        return obj.current_student or obj.current_staff or obj.current_admin



class AccountAdmin(admin.ModelAdmin):
    list_display = ["ghp_user", 'balance', 'last_update']
    list_filter = ['balance', 'last_update']
    search_fields = ['ghp_user__first_name', 'ghp_user__last_name', 'ghp_user__email']
    ordering = ['balance', 'last_update']

    readonly_fields = ["ghp_user", 'balance', 'last_update']

    @admin.display(ordering="ghp_user__last_name")
    def user_last_name(self, obj):
        return str(obj.ghp_user) # obj.ghp_user.first_name + ' ' + obj.ghp_user.last_name


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

    list_display = ['ghp_user', 'ghp_user_piece_id', 'length', 'width', 'height', 'size', 'bisque_temp', 'glaze_temp', 'price', 'date', 'image', 'email', ]
    list_display_links = ['ghp_user', 'ghp_user_piece_id']

    @admin.display(ordering="ghp_user__last_name")
    def name(self, obj):
        return str(obj.ghp_user.first_name) + ' ' + str(obj.ghp_user.last_name)

    @admin.display(ordering="ghp_user__email")
    def email(self, obj):
        return str(obj.ghp_user.email)





    readonly_fields = ['ghp_user_piece_id', 'date', 'ghp_user', 'name', 'email', 'length', 'width', 'height', 'size', 'price','bisque_temp', ]
    list_filter = ['glaze_temp', 'bisque_temp', 'date', 'ghp_user', 'length', 'width', 'height', 'size', 'price' ]
    search_fields = ['ghp_user__first_name', 'ghp_user__last_name', 'ghp_user__email']
    ordering = ['-date', 'ghp_user__last_name', 'ghp_user__first_name']

class LedgerAdmin(admin.ModelAdmin):

    list_display = ['transaction_id', 'date', 'ghp_user', 'amount', 'transaction_type', 'note', 'piece']
    list_filter = ['transaction_type', 'date', 'ghp_user']
    search_fields = ['ghp_user__first_name', 'ghp_user__last_name', 'ghp_user__email', 'transaction_type', 'date', 'note']
    ordering = ['-date', 'ghp_user__last_name', 'ghp_user__first_name']

    readonly_fields = ['transaction_id', 'ghp_user_transaction_number', 'date', 'ghp_user', 'amount', 'transaction_type', 'piece']

admin.site.register(GHPUser, GHPUserAdmin)
admin.site.register(Account, AccountAdmin)
admin.site.register(Piece, PieceAdmin)
admin.site.register(Ledger, LedgerAdmin)
