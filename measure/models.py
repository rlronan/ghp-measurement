import datetime
from django.utils import timezone
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
import numpy as np
import decimal
from .constants import GLAZE_TEMPS
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
    # auto primary key here
    user = models.OneToOneField(User, on_delete=models.CASCADE, blank=True, null=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length = 12, unique=False, blank=True, default='')
    email = models.EmailField(unique=True, max_length=200, blank=True)

    current_student = models.BooleanField(default=False)
    current_staff = models.BooleanField(default=False)
    current_admin = models.BooleanField(default=False)  

    last_measure_date = models.DateField(null=True)

    consent = models.BooleanField(default=False)
    consent_date = models.DateField(null=True)

    class Meta:
        managed = True
        db_table = 'ghp_user'

    def save(self, *args, **kwargs):
        #do_something()
        super().save(*args, **kwargs)  # Call the "real" save() method.
        #do_something_else()

        # Create a user for the GHPUser if they don't have one
        if not User.objects.filter(ghpuser=self).exists():
            User.objects.create_user(username=self.email, email=self.email, 
                                     password='password', ghpuser=self, 
                                     first_name=self.first_name, 
                                     last_name=self.last_name)
            
            # Update the GHPUser object with the new user
            self.user = User.objects.get(ghpuser=self)

            # Save the GHPUser object
            super().save(*args, **kwargs)
            
        
        # Create an account for the user if they don't have one
        if not Account.objects.filter(ghp_user=self).exists():
            Account.objects.create(ghp_user=self, balance=0.00, last_update=timezone.now())

    def get_name(self):
        return self.first_name + ' ' + self.last_name

    def __str__(self):
        s = self.first_name + ' ' + self.last_name
        if self.current_admin:
            s += ' (Admin)'
        elif self.current_staff:
            s += ' (Faculty/Resident)'
        elif self.current_student:
            s += ' (Student)'
        return s


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
    course_number = models.CharField(max_length=4, blank=True)
    piece_description = models.CharField(max_length=1000, blank=True)
    glaze_description = models.CharField(max_length=1000, blank=True)
    glaze_temp = models.CharField(max_length=4, choices=GLAZE_TEMPS, default="Δ 10") # imported from constants.py

    note = models.CharField(max_length=1000, blank=True)
    image = models.ImageField(upload_to='images/', blank=True, null=True)
    bisque_fired = models.BooleanField(blank=True, null=True)
    glaze_fired = models.BooleanField(blank=True, null=True)



    # glaze_temp_help_text = """
    # Glaze firing temperature. Cone 10 is the 'standard'. 
    # You will be charged for the glaze firing if you select a temperature.
    # Select 'None' if you do not wish to glaze this piece, or if you do not know 
    # the glaze firing temperature you want to use.  
    # """
                                  
    #help_text=glaze_temp_help_text
    class Meta:
        managed = True
        db_table = 'piece'
        constraints = [
            models.CheckConstraint(check=models.Q(length__gte=0.5), name='length_gte_0.5', violation_error_message="Length must be at least 0.5 inches"),
            models.CheckConstraint(check=models.Q(width__gte=0.5), name='width_gte_0.5', violation_error_message="Width must be at least 0.5 inches"),
            models.CheckConstraint(check=models.Q(height__gte=3.0), name='height_gte_3.0', violation_error_message="Height must be at least 3 inches"),
        ]
    
    
    def save(self, *args, **kwargs):

        # get previous (maximum) ghp_user_piece_id so we can increment it
        self.ghp_user_piece_id = Piece.objects.filter(ghp_user=self.ghp_user).count() + 1
        self.date = timezone.now()

        # Check the size of the piece is correct (length * width * height) up to 2 decimal places
        size_test = self.length * self.width * self.height
        size_test = size_test.quantize(decimal.Decimal('0.01'), rounding=decimal.ROUND_UP)
        assert(np.abs(size_test - self.size) < 0.01)

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


        # update the last measure date for the user
        self.ghp_user.last_measure_date = self.date

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


