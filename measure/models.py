import datetime

from django.db import models
from django.utils import timezone

# Create your models here.

class GHPUser(models.Model):
#    id = models.BigAutoField(primary_key=True)
    # auto primary key here
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length = 12, unique=True, blank=True, default='')
    email = models.EmailField(unique=True, max_length=200, blank=True)
    dob = models.DateField(blank=True, null=True)
    current_student = models.BooleanField(default=False)
    current_teacher = models.BooleanField(default=False)
    current_staff = models.BooleanField(default=False)
    current_admin = models.BooleanField(default=False)  

    class Meta:
        managed = True
        db_table = 'ghp_user'
    def get_name(self):
        return self.first_name + ' ' + self.last_name

    def __str__(self):
        s = self.first_name + ' ' + self.last_name
        if self.current_admin:
            s += ' (admin)'
        elif self.current_staff:
            s += ' (staff)'
        elif self.current_teacher:
            s += ' (teacher)'
        elif self.current_student:
            s += ' (student)'
        return s

class Account(models.Model):
    # Pk is ghp_user_id
    ghp_user = models.OneToOneField('GHPUser', models.DO_NOTHING, primary_key=True)
    balance = models.DecimalField(default=0.00, max_digits=10, decimal_places=2)
    last_update = models.DateTimeField()

    class Meta:
        managed = True
        db_table = 'account'

    def __str__(self):
        s_end = ' -$' + str(self.balance * -1) if self.balance < 0 else ' $' + str(self.balance)
        return str(self.ghp_user) + s_end

class Course(models.Model):
    # auto primary key here
    code = models.CharField(max_length=30, help_text="Code for the course, e.g. 'W7', 'W1'")
    name = models.CharField(max_length=300, help_text="Full name for the course, without the term or teacher e.g. 'INT./ADV. Handbuilding', 'Beginner Wheel")

    class Meta:
        managed = True
        db_table = 'course'
    
    def __str__(self):
        return self.name

class Location(models.Model):
    room = models.CharField(max_length=300, blank=False, help_text="e.g. '2nd Floor Wheel', or '301'")
    address = models.CharField(max_length=300, blank=True, help_text="Building address")
    type = models.CharField(max_length=50, blank=True, help_text="e.g. 'Wheel', 'Handbuilding', 'Glaze'")
    
    class Meta:
        managed = True
        db_table = 'location'

    def __str__(self):
        return self.room

class Term(models.Model):
    name = models.CharField(max_length=200, blank=True, help_text="Name of the term, e.g. 'Spring 2023', or, 'Summer-8-Week 2023'")
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    current = models.BooleanField(default=False)

    class Meta:
        managed = True
        db_table = 'term'

    def __str__(self):
        return self.name + ' (' + str(self.start_date) + ' - ' + str(self.end_date) + ')'

# class DayOfWeek(models.TextChoices):
#     M = 'M', _('Monday')
#     T = 'T', _('Tuesday')
#     W = 'W', _('Wednesday')
#     R = 'R', _('Thursday')
#     F = 'F', _('Friday')
#     S = 'S', _('Saturday')
#     U = 'U', _('Sunday')


class CourseInstance(models.Model):
    #id = models.IntegerField(primary_key=True)
    # auto primary key here
    name = models.CharField(max_length=1000, blank=True, help_text="Name of the course instance, e.g. 'W15 INT/ADV Wheel Throwing w/ Haakon', or 'ST4 Glass Casting w/ Jessi'")
    term = models.ForeignKey(Term, models.SET_NULL, null=True, help_text="Term the course instance is in. e.g., 'Spring 2023', or, 'Summer-8-Week 2023'")
    teachers = models.ManyToManyField(GHPUser, related_name='teachers') # need to change the form for this
    students = models.ManyToManyField(GHPUser, related_name='students') # need to change the form for this
    course = models.ForeignKey(Course, models.SET_NULL, null=True, blank=True)
    location = models.ForeignKey(Location, models.SET_NULL, null=True, blank=True)
    type = models.CharField(max_length=100, blank=True)
    weekday = models.CharField(max_length=100, blank=True) #models.ForeignKey(DayOfWeek, models.DO_NOTHING, blank=True, null=True)
    start_time = models.TimeField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'course_instance'

    def __str__(self):
        if self.start_time is None or self.end_time is None:
            s_end = ' (' + str(self.term.name) + ')' + ' ' + self.weekday
        else:
            s_end = ' (' + str(self.term.name) + ')' + ' ' + self.weekday \
                + ' ' + str(self.start_time) + ' - ' + str(self.end_time)
        if self.teachers.count() > 1:
            return self.name + ' with ' + str(self.teachers.all().get_name()) + s_end
        elif self.teachers.count() == 1:
            return self.name + ' with ' + str(self.teachers.first().get_name()) + s_end
        else:
            return self.name + s_end
        #     return self.name + ' with ' + str(self.teachers.objects.filter()) \
        #         + ' (' + str(self.term.name) + ')' + ' ' + self.weekday
        # return self.name + ' with ' + str(self.teachers) \
        #         + ' (' + str(self.term.name) + ')' + ' ' + self.weekday \
        #         + ' ' + str(self.start_time) + ' - ' + str(self.end_time)

class Piece(models.Model):
    # id = models.IntegerField(primary_key=True)
    # auto pk 
    ghp_user = models.ForeignKey(GHPUser, models.CASCADE, null=False)
    ghp_user_piece_id = models.IntegerField(default= 1 )
    length = models.DecimalField(default=0.00, max_digits=10, decimal_places=2)
    width = models.DecimalField(default=0.00, max_digits=10, decimal_places=2)
    height = models.DecimalField(default=0.00, max_digits=10, decimal_places=2)
    size = models.DecimalField(default=0.00, max_digits=10, decimal_places=2)
    price = models.DecimalField(default=0.00, max_digits=10, decimal_places=2)
    bisque_fired = models.BooleanField(blank=True, null=True)
    glaze_fired = models.BooleanField(blank=True, null=True)
    damaged = models.BooleanField(blank=True, null=True)
    course = models.ForeignKey(CourseInstance, models.SET_NULL, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'piece'
    def __str__(self):
        return str(self.ghp_user) + ' #' + str(self.ghp_user_piece_id) + ' ' \
                + str(self.length) + 'x' + str(self.width) + 'x' \
                + str(self.height) + ' ' + '$' +  str(self.price)

class Ledger(models.Model):
    transaction_id = models.AutoField(primary_key=True)
    date = models.DateTimeField()
    ghp_user = models.ForeignKey(GHPUser, models.SET_NULL, null=True)
    ghp_user_transaction_number = models.IntegerField(default= 1 )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=100, blank=True)
    note = models.CharField(max_length=1000, blank=True)
    piece = models.ForeignKey(Piece, models.SET_NULL, null=True, blank=True)

    class Meta:
        managed = True
        db_table = 'ledger'

    def __str__(self):
        return self.ghp_user.first_name[:1] + '. ' + self.ghp_user.last_name + ' trans. #' + str(self.ghp_user_transaction_number) + ' ' \
                + self.date.strftime(r'%m/%d/%y') + ' ' + self.date.strftime(r'%H:%M:%S') + ' $' + str(self.amount) + ' ' \
                + self.transaction_type + ' (' + self.note + ')'






