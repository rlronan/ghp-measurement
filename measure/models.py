import datetime
from django.utils import timezone
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
import decimal
# Create your models here.

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


class GHPUser(models.Model):
#    id = models.BigAutoField(primary_key=True)
    # auto primary key here
    #user = models.OneToOneField(User, on_delete=models.CASCADE, blank=True, null=True)
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

    def save(self, *args, **kwargs):
        #do_something()
        super().save(*args, **kwargs)  # Call the "real" save() method.
        #do_something_else()
        # Create an account for the user if they don't have one
        if not Account.objects.filter(ghp_user=self).exists():
            Account.objects.create(ghp_user=self, balance=0.00, last_update=timezone.now())

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
    constraints = [
            models.CheckConstraint(check=models.Q(end_date__gte=start_date), name='end_date_gte_start_date'),
        ]
    def __str__(self):
        return self.name + ' (' + str(self.start_date) + ' - ' + str(self.end_date) + ')'

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
        return '(' + self.course.code + ') ' +self.course.name 
        # if self.start_time is None or self.end_time is None:
        #     s_end = ' ' + self.weekday #' (' + str(self.term.name) + ')' 
        # else:
        #     s_end = ' ' + self.course.code + ' (' + self.weekday + ' ' +  str(self.start_time.hour) + ':' + str(self.start_time.minute) + ')' #+ ' - ' + str(self.end_time)
        # if self.teachers.count() > 1:
        #     return self.name + ' with ' + ' +'.join(self.teachers.all().get_name()) + s_end
        # elif self.teachers.count() == 1:
        #     return self.name + ' with ' + str(self.teachers.first().get_name()) + s_end
        # else:
        #     return self.name + s_end





class Piece(models.Model):
    # id = models.IntegerField(primary_key=True)
    # auto pk 
    ghp_user = models.ForeignKey(GHPUser, models.CASCADE, null=False)
    ghp_user_piece_id = models.IntegerField(default= 1 )
    date = models.DateField(blank=True, null=True)
    length = models.DecimalField(default=0.00, max_digits=10, decimal_places=2)
    width = models.DecimalField(default=0.00, max_digits=10, decimal_places=2)
    height = models.DecimalField(default=0.00, max_digits=10, decimal_places=2)
    size = models.DecimalField(default=0.00, max_digits=10, decimal_places=2)
    price = models.DecimalField(default=0.00, max_digits=10, decimal_places=2)
    bisque_fired = models.BooleanField(blank=True, null=True)
    glaze_fired = models.BooleanField(blank=True, null=True)
    damaged = models.BooleanField(blank=True, null=True)
    course = models.ForeignKey(CourseInstance, models.SET_NULL, blank=True, null=True)
    piece_description = models.CharField(max_length=1000, blank=True)
    glaze_description = models.CharField(max_length=1000, blank=True)
    note = models.CharField(max_length=1000, blank=True)

    GLAZE_TEMPS  = [
        ("10", "Cone 10"),
        ("06", "Cone 06"),
        ("04", "Cone 04"),
        ("02", "Cone 02"),
        ("14", "Cone 14"),
        ("None", "None"),
    ]


    # glaze_temp_help_text = """
    # Glaze firing temperature. Cone 10 is the 'standard'. 
    # You will be charged for the glaze firing if you select a temperature.
    # Select 'None' if you do not wish to glaze this piece, or if you do not know 
    # the glaze firing temperature you want to use.  
    # """
    glaze_temp = models.CharField(max_length=4, choices=GLAZE_TEMPS, default="Cone 10",
                                  )
    #help_text=glaze_temp_help_text
    class Meta:
        managed = True
        db_table = 'piece'
        constraints = [
            models.CheckConstraint(check=models.Q(length__gte=0.25), name='length_gte_0.25'),
            models.CheckConstraint(check=models.Q(width__gte=0.25), name='width_gte_0.25'),
            models.CheckConstraint(check=models.Q(height__gte=1.5), name='height_gte_1.5'),
        ]
    
    
    def save(self, *args, **kwargs):

        # get previous (maximum) ghp_user_piece_id so we can increment it
        self.ghp_user_piece_id = Piece.objects.filter(ghp_user=self.ghp_user).count() + 1
        self.date = timezone.now()

        # Check the size of the piece is correct (length * width * height) up to 2 decimal places
        size_test = self.length * self.width * self.height
        print(size_test, type(size_test), self.size, type(self.size))
        size_test = size_test.quantize(decimal.Decimal('0.01'), rounding=decimal.ROUND_UP)
        assert(size_test == self.size)

        # price should be depdent on size and whethere or not it is being glazed
        # This assumes 
        super().save(*args, **kwargs)  # Call the "real" save() method.
        #do_something_else()
        self.ghp_user_transaction_number = Ledger.objects.filter(ghp_user=self.ghp_user).count() + 1


        # if the piece is being glazed, create a ledger entry for the bisque and glaze firing fees
        # otherwise, just create a ledger entry for the bisque firing fee
        if self.glaze_temp != 'None':
            # Create an Ledger object for the bisque firing fee. 
            # Reduce the price by half to account for the glaze firing fee
            if not Ledger.objects.filter(piece=self).exists():
                Ledger.objects.create(
                    date = self.date,
                    ghp_user=self.ghp_user,
                    ghp_user_transaction_number=self.ghp_user_transaction_number,
                    amount=-1*self.price/2,
                    transaction_type='Bisque Firing Fee',
                    note='Bisque Firing Fee for Piece #' + str(self.ghp_user_piece_id),
                    piece=self
                    )
            else: 
                raise ValueError('Firing fee Ledger entry already exists for this piece')
            # Create an Ledger object for the glaze firing fee
            #if not Ledger.objects.filter(piece=self).exists():
            Ledger.objects.create(
                date = self.date,
                ghp_user=self.ghp_user,
                ghp_user_transaction_number=self.ghp_user_transaction_number + 1,
                amount=-1*self.price/2,
                transaction_type='Glaze Firing Fee',
                note='Glaze Firing Fee for Piece #' + str(self.ghp_user_piece_id),
                piece=self
                )
        else:
            # Create an Ledger object for the bisque firing fee
            # Do not reduce the price because it incorporates no glaze firing fee
            if not Ledger.objects.filter(piece=self).exists():
                Ledger.objects.create(
                    date = self.date,
                    ghp_user=self.ghp_user,
                    ghp_user_transaction_number=self.ghp_user_transaction_number,
                    amount=-1*self.price,
                    transaction_type='Bisque Firing Fee',
                    note='Bisque Firing Fee for Piece #' + str(self.ghp_user_piece_id),
                    piece=self
                    )



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

    def save(self, *args, **kwargs):
        #do_something()
        super().save(*args, **kwargs)  # Call the "real" save() method.
        
        # Modify user's Account balance by amount, and update Account.last_update
        if self.ghp_user is not None:
            self.ghp_user.account.balance += self.amount
            self.ghp_user.account.last_update = timezone.now()
            self.ghp_user.account.save()
        else:
            print('No ghp_user for this transaction')
            raise ValueError('No ghp_user for this transaction')


