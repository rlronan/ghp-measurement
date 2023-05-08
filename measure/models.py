import datetime
from django.utils import timezone
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
import numpy as np
import decimal
from .constants import GLAZE_TEMPS, USER_FIRING_SCALE, STAFF_FIRING_SCALE, USER_GLAZING_SCALE, STAFF_GLAZING_SCALE, MINIMUM_PRICE
from django.db import IntegrityError
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


class GHPUser(User):
    # auto primary key here
    #user = models.OneToOneField(User, on_delete=models.CASCADE, blank=True, null=True)
    #first_name = models.CharField(max_length=100)
    #last_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length = 12, unique=False, blank=True, default='')
    #email = models.EmailField(unique=True, max_length=200, blank=True)

    current_student = models.BooleanField(default=False)
    current_staff = models.BooleanField(default=False)
    current_admin = models.BooleanField(default=False)  

    last_measure_date = models.DateField(null=True)

    consent = models.BooleanField(default=False)
    consent_date = models.DateField(null=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    class Meta:
        managed = True
        db_table = 'ghp_user'

    def save(self, *args, **kwargs):
        #do_something()
        print("Saving GHPUser: " + self.first_name + " " + self.last_name )

#         # Check if the user exists, if not, create one
#         if self.user is None:
#             print("Creating user for GHPUser: " + self.first_name + " " + self.last_name)
#             try:
#                 # don't think I can give a ghpuser attribute here. The user is created before the GHPUser object
#                 user = User.objects.create_user(username=self.email, email=self.email,
#                                                 password='password', 
#                                                 first_name=self.first_name,
#                                                 last_name=self.last_name)
#                 print("User created for GHPUser")
# # 
#             except IntegrityError as e:
#                 print(e)
#                 print("User may already exist with that email address")
#                 user = User.objects.get(email=self.email)
#                 print("User found: " + str(user))
            
#                 # If the User is a superuser, or staff, then we probably 
#                 # don't want to attach this GHPUser to it
#                 if user.is_superuser or user.is_staff:
#                     print("User is a superuser or staff, not attaching GHPUser to it")
#                     user = None
# # TODO: This does not feel safe. 
#                 else:
#                     print("User is not a superuser or staff, attaching GHPUser to it")
#                     # Update the GHPUser object with the new user
#                     self.user = user
#                     print("User attached to GHPUser")


#             # Update the GHPUser object with the new user
#             self.user = user








        # # Create a user for the GHPUser if they don't have one
        # # Check if a user exists for the GHPUser, if not create one
        # # print(User.objects.all())
        # # print(User.objects.filter(ghpuser=self), User.objects.filter(ghpuser=self).exists())

        # # check if self.user is None, if so, then create a user. If not, then update the user
        # if self.user is None:
        #     User_exists = False
        # else:
        #     User_exists = True


        # # running a bug here where User.objects.filter(ghpuser=self) returns the admin User object
        # # who has no associated GHPUser object, so it's always true that User.objects.filter(ghpuser=self).exists().
        # # Not sure why the admin user is being returned, but I'm going to try to fix it by checking
        # # if the user has a ghpuser attribute, which should only be true for the GHPUser objects
        # if User.objects.filter(ghpuser=self).exists():

        #     # need to check if any of the users returned have a ghpuser attribute
        #     # if not, then the admin user is being returned
        #     for user in User.objects.filter(ghpuser=self):
        #         if not hasattr(user, 'ghpuser'):
        #             print("Admin user returned, ignoring")
        #         else:
        #             User_exists = True
        #             # User exists for the GHPUser, update the User
        #             print("User found for GHPUser, updating user")
        #             print("User: " + str(self.user))
        #             # Update the user with the new GHPUser info
        #             self.user.first_name = self.first_name
        #             self.user.last_name = self.last_name
        #             self.user.email = self.email
        #             self.user.save()
        #             print("User updated")
        #             break


        # if not User_exists:
        #     print("Assigning user to GHPUser")
        #     user = User.objects.create_user(username=self.email, email=self.email, 
        #                             password='password', ghpuser=self, 
        #                             first_name=self.first_name, 
        #                             last_name=self.last_name)

        #     # Update the GHPUser object with the new user
        #     self.user = user
        #     print("User assigned to GHPUser")
        #     User_exists = True

        super().save(*args, **kwargs)  # Call the "real" save() method.
        
        # Create an account for the user if they don't have one
        # Should not have the same bug as above because User objects don't have an account attribute
        if not Account.objects.filter(ghp_user=self).exists():
            Account.objects.create(ghp_user=self, balance=0.00, last_update=timezone.now())

    # def get_name(self):
    #     return self.first_name + ' ' + self.last_name

    def get_price_scale(self):
        if self.current_admin or self.current_staff:
            return (STAFF_FIRING_SCALE, STAFF_GLAZING_SCALE)
        elif self.current_student:
            return (USER_FIRING_SCALE, USER_GLAZING_SCALE)
        else:
            # later we can add a default scale for non-students if ghp ever wants
            return (USER_FIRING_SCALE, USER_GLAZING_SCALE)



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
    firing_price = models.DecimalField(default=0.00, max_digits=10, decimal_places=2)
    glazing_price = models.DecimalField(default=0.00, max_digits=10, decimal_places=2)

    course_number = models.CharField(max_length=4, blank=True)
    piece_description = models.CharField(max_length=1000, blank=True)
    glaze_description = models.CharField(max_length=1000, blank=True)
    glaze_temp = models.CharField(max_length=4, choices=GLAZE_TEMPS, default="Δ 10") # imported from constants.py

    note = models.CharField(max_length=1000, blank=True)
    image = models.ImageField(upload_to='images/', blank=True, null=True)
    bisque_fired = models.BooleanField(default=False)
    glaze_fired = models.BooleanField(default=False)



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
        try:
            assert(np.abs(size_test - self.size) < 0.01)
        except AssertionError:
            print("Size is not correct, recalculating")
            print("size_test: " + str(size_test))
            print("self.size: " + str(self.size))
            print("np.abs(size_test - self.size): " + str(np.abs(size_test - self.size)))
            print("type(size_test): " + str(type(size_test)))
            print("type(self.size): " + str(type(self.size)))
            print("type(np.abs(size_test - self.size)): " + str(type(np.abs(size_test - self.size))))
            self.size = size_test
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


