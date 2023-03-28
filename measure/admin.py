from django.contrib import admin

from .models import User, Account, Course, Location, Term, CourseInstance, Piece, Ledger

# Register your models here.
admin.site.register(User)
admin.site.register(Account)
admin.site.register(Course)
admin.site.register(Location)
admin.site.register(Term)
admin.site.register(CourseInstance)
admin.site.register(Piece)
admin.site.register(Ledger)
