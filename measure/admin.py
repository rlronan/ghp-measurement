from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from django.db.models.functions import Concat
from django.db.models import Value
from .models import GHPUser, Account, Course, Location, Term, CourseInstance, Piece, Ledger
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
            return queryset.filter(Q(current_student=True) | Q(current_teacher=True) | Q(current_staff=True) | Q(current_admin=True))
        if self.value() == "false":
            return queryset.filter(Q(current_student=False) & Q(current_teacher=False) & Q(current_staff=False) & Q(current_admin=False))


@admin.action(description="Mark selected users as current students")
def make_students(modeladmin, request, queryset):
    queryset.update(current_student=True)

@admin.action(description="Mark selected users as current teachers")
def make_teachers(modeladmin, request, queryset):
    queryset.update(current_teacher=True)

@admin.action(description="Mark selected users as current staff")
def make_staff(modeladmin, request, queryset):
    queryset.update(current_staff=True)

@admin.action(description="Mark selected users as current admins")
def make_admins(modeladmin, request, queryset):
    queryset.update(current_admin=True)

@admin.action(description="Mark selected users as not current students, teachers, staff, nor admins")
def make_not_current(modeladmin, request, queryset):
    queryset.update(current_student=False, current_teacher=False, current_staff=False, current_admin=False)



class GHPUserAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 
                    'phone_number', 'dob', 'current_student', 'current_teacher',
                      'current_staff', 'current_admin', 'current')
    list_filter = ('current_student', 'current_teacher', 'current_staff', 'current_admin', CurrentUserFilter)
    search_fields = ('first_name', 'last_name', 'email', 'phone_number')
    ordering = ('last_name', 'first_name', 'email')
    actions = [make_students, make_teachers, make_staff, make_admins, make_not_current]

    @admin.display(description='Current', boolean=True)
    def current(self, obj):
        return obj.current_student or obj.current_teacher or obj.current_staff or obj.current_admin



class AccountAdmin(admin.ModelAdmin):
    list_display = ("ghp_user", 'balance', 'last_update')
    list_filter = ('balance', 'last_update')
# TODO: add search by user

    # search fields doesn't work with foreign keys
    search_fields = ( 'balance', 'last_update')
    ordering = ('balance', 'last_update')


    # @admin.display(ordering=Concat("ghp_user__last_name", Value(" "), "ghp_user__first_name"))
    # def full_name(self, obj):
    #     return self.obj.first_name + " " + self.obj.last_name

    @admin.display(ordering="ghp_user__last_name")
    def user_last_name(self, obj):
        return str(obj.ghp_user) # obj.ghp_user.first_name + ' ' + obj.ghp_user.last_name

class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    list_filter = ('name', 'code')
    search_fields = ('name', 'code')
    ordering = ('name', 'code')


class LocationAdmin(admin.ModelAdmin):
    list_display = ('room', 'address', 'type')
    list_filter = ('room', 'address', 'type')
    search_fields = ('room', 'address', 'type')
    ordering = ('room', 'address', 'type')


class TermAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'current')
    list_filter = ('name', 'start_date', 'end_date', 'current')
    search_fields = ('name', 'start_date', 'end_date', 'current')
    ordering = ('name', 'start_date', 'end_date', 'current')

    @admin.display(description='Current', boolean=True)
    def current(self, obj):
        return obj.current

class CourseInstanceAdmin(admin.ModelAdmin):
    list_display = ('name', 'term', 'course', 'location', 'type', 'weekday', 'start_time')
    list_filter = ('name', 'term',  'course', 'location', 'type', 'weekday', 'start_time')
    search_fields = ('name', 'term', 'course', 'location', 'type', 'weekday', 'start_time')
    ordering = ('name', 'term', 'course', 'location', 'type', 'weekday', 'start_time')

class PieceAdmin(admin.ModelAdmin):
    list_display = ('ghp_user', 'ghp_user_piece_id', 'length', 'width', 'height', 'size', 'glaze_temp', 'price', 'date')
    list_filter = ('ghp_user', 'glaze_temp', 'date')
    search_fields = ('ghp_user', 'length', 'width', 'height', 'size', 'glaze_temp', 'price', 'date')

class LedgerAdmin(admin.ModelAdmin):

    list_display = ('transaction_id', 'date', 'ghp_user', 'amount', 'transaction_type', 'note', 'piece')
    list_filter = ('ghp_user', 'transaction_type', 'date')
# TODO: add search by user
    search_fields = ('transaction_type', 'date', 'note')



admin.site.register(GHPUser, GHPUserAdmin)
admin.site.register(Account, AccountAdmin)
admin.site.register(Course, CourseAdmin)
admin.site.register(Location, LocationAdmin)
admin.site.register(Term, TermAdmin)
admin.site.register(CourseInstance, CourseInstanceAdmin)
admin.site.register(Piece, PieceAdmin)
admin.site.register(Ledger, LedgerAdmin)
