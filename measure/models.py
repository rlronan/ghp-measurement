from django.db import models

# Create your models here.

class User(models.Model):
#    id = models.BigAutoField(primary_key=True)
    # auto primary key here
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_number = models.IntegerField(unique=True, blank=True, null=True)
    email = models.EmailField(unique=True, max_length=200, blank=True)
    dob = models.DateTimeField(blank=True, null=True)
    current_student = models.BooleanField(default=False)
    current_teacher = models.BooleanField(default=False)
    current_staff = models.BooleanField(default=False)
    current_admin = models.BooleanField(default=False)

    class Meta:
        managed = True
        db_table = 'user'

class Account(models.Model):
    # Pk is user_id
    user = models.OneToOneField('User', models.DO_NOTHING, primary_key=True)
    balance = models.DecimalField(default=0.00, max_digits=10, decimal_places=2)
    last_update = models.DateTimeField()

    class Meta:
        managed = True
        db_table = 'account'


class Course(models.Model):
    #id = models.IntegerField(primary_key=True)
    # auto primary key here
    code = models.CharField(max_length=30, help_text="Code for the course, e.g. 'W7', 'W1'")
    name = models.CharField(max_length=300, help_text="Full name for the course, without the term or teacher e.g. 'INT./ADV. Handbuilding', 'Beginner Wheel")

    class Meta:
        managed = True
        db_table = 'course'

class Location(models.Model):
    room = models.CharField(max_length=300, blank=False, help_text="e.g. '2nd Floor Wheel', or '301'")
    address = models.CharField(max_length=300, blank=True, help_text="Building address")
    type = models.CharField(max_length=50, blank=True, help_text="e.g. 'Wheel', 'Handbuilding', 'Glaze'")
    
    class Meta:
        managed = True
        db_table = 'location'

class Term(models.Model):
    name = models.CharField(max_length=200, blank=True, help_text="Name of the term, e.g. 'Spring 2023', or, 'Summer-8-Week 2023'")
    start_date = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)
    current = models.BooleanField(default=False)

    class Meta:
        managed = True
        db_table = 'term'

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
    teachers = models.ManyToManyField(User, related_name='teachers')
    students = models.ManyToManyField(User, related_name='students')
    course = models.ForeignKey(Course, models.SET_NULL, null=True)
    location = models.ForeignKey(Location, models.SET_NULL, null=True)
    type = models.CharField(max_length=100, blank=True)
    weekday = models.CharField(max_length=100, blank=True) #models.ForeignKey(DayOfWeek, models.DO_NOTHING, blank=True, null=True)
    start_time = models.TimeField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'course_instance'

class Piece(models.Model):
    # id = models.IntegerField(primary_key=True)
    # auto pk 
    user = models.ForeignKey(User, models.CASCADE, null=False)
    user_piece_id = models.IntegerField(default= 1 )
    length = models.DecimalField(default=0.00, max_digits=10, decimal_places=4)
    width = models.DecimalField(default=0.00, max_digits=10, decimal_places=4)
    height = models.DecimalField(default=0.00, max_digits=10, decimal_places=4)
    size = models.DecimalField(default=0.00, max_digits=10, decimal_places=4)
    bisque_fired = models.BooleanField(blank=True, null=True)
    glaze_fired = models.BooleanField(blank=True, null=True)
    damaged = models.BooleanField(blank=True, null=True)
    course = models.ForeignKey(Course, models.SET_NULL, null=True)

    class Meta:
        managed = True
        db_table = 'piece'


class Ledger(models.Model):
    transaction_id = models.AutoField(primary_key=True)
    date = models.DateTimeField()
    user = models.ForeignKey(User, models.SET_NULL, null=True)
    user_transaction_number = models.IntegerField(default= 1 )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=100, blank=True)
    note = models.CharField(max_length=1000, blank=True)
    piece = models.ForeignKey(Piece, models.SET_NULL, null=True)

    class Meta:
        managed = True
        db_table = 'ledger'






