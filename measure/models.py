import datetime
from django.utils import timezone
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
import numpy as np
import decimal
from .constants import GLAZE_TEMPS,  BISQUE_TEMPS, USER_FIRING_SCALE, STAFF_FIRING_SCALE, \
    USER_GLAZING_SCALE, STAFF_GLAZING_SCALE, MINIMUM_PRICE, TRANSACTION_TYPES
from django.db import IntegrityError
from django.core.exceptions import ValidationError

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
    ##phone_number = models.CharField(max_length = 12, unique=False, blank=True, default='') # renove 12/29/23
    #email = models.EmailField(unique=True, max_length=200, blank=True)

    current_student = models.BooleanField(default=False)
    current_staff = models.BooleanField(default=False)
    current_admin = models.BooleanField(default=False)  

    last_measure_date = models.DateField(null=True)

    consent = models.BooleanField(default=False)
    consent_date = models.DateField(null=True)


    GREENWICH = 'Greenwich'
    CHELSEA = 'Chelsea'
    BOTH = 'Both'
    
    LOCATION_CHOICES = [
        (GREENWICH, 'Greenwich'),
        (CHELSEA, 'Chelsea'),
        (BOTH, 'Both'),
    ]

    current_location = models.CharField(
        max_length=10,
        choices=LOCATION_CHOICES,
        default=GREENWICH,  # You can set a default value if needed
    )
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    class Meta:
        managed = True
        db_table = 'ghp_user'

    def save(self, *args, **kwargs):
        #do_something()

        UPDATING = False
        if not self._state.adding:
            UPDATING = True

        if UPDATING:
            print("UPDATING GHPUser: " + self.first_name + " " + self.last_name )
        else:
            print("SAVING GHPUser: " + self.first_name + " " + self.last_name )
        super().save(*args, **kwargs)  # Call the "real" save() method.
        
        # Create an account for the user if they don't have one
        # Should not have the same bug as above because User objects don't have an account attribute

        # print("Checking if user has an account")
        if not Account.objects.filter(ghp_user=self).exists():
            Account.objects.create(ghp_user=self, balance=0.00, last_update=timezone.now())
            print("Account created for GHPUser")
        else:
            print("Account already exists for GHPUser")

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

    def get_balance(self):
        if not Account.objects.filter(ghp_user=self).exists():
            print("WARNING: User does not have an account, but they should! Creating one")
            Account.objects.create(ghp_user=self, balance=0.00, last_update=timezone.now())
            print("Account created for GHPUser")
        return Account.objects.get(ghp_user=self).balance

    def get_location(self):
        if self.current_location == 'Both':
            return 'None'
        else: return self.current_location 

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
    length = models.DecimalField(max_digits=5, decimal_places=1)
    width = models.DecimalField(max_digits=5, decimal_places=1)
    height = models.DecimalField( max_digits=5, decimal_places=1)
    size = models.DecimalField(default=0.00, max_digits=10, decimal_places=2)
    price = models.DecimalField(default=0.00, max_digits=10, decimal_places=2)
    firing_price = models.DecimalField(default=0.00, max_digits=10, decimal_places=2)
    glazing_price = models.DecimalField(default=0.00, max_digits=10, decimal_places=2)

    course_number = models.CharField(max_length=4, blank=True)
    bisque_temp = models.CharField(max_length=4, choices=BISQUE_TEMPS, default="06") # imported from constants.py

    glaze_temp = models.CharField(max_length=4, choices=GLAZE_TEMPS, default="10") # imported from constants.py

    note = models.CharField(max_length=1000, blank=True)
    #TODO: FIX IMAGE FIELD FOR HEROKU
    image = models.ImageField(upload_to='images/', blank=True, null=True)

    ## Added 12/29/23:
    GREENWICH = 'Greenwich'
    CHELSEA = 'Chelsea'
    
    LOCATION_CHOICES = [
        (GREENWICH, 'Greenwich'),
        (CHELSEA, 'Chelsea'),
    ]

    piece_location = models.CharField(
        max_length=10,
        choices=LOCATION_CHOICES,
        default=GREENWICH,  # You can set a default value if needed
    )

    ## Remove these four on 12/29/23:
    ## piece_description = models.CharField(max_length=1000, blank=True)
    ## glaze_description = models.CharField(max_length=1000, blank=True)
    ## bisque_fired = models.BooleanField(default=False)
    ## glaze_fired = models.BooleanField(default=False)



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

            models.CheckConstraint(check=models.Q(length__lte=21.0)  & models.Q(width__lte=21.0), name='length_and_width_lte_21.0', violation_error_message="Length amd width must be less than or equal to 21 inches"),
            models.CheckConstraint(check=models.Q(height__lte=22.0), name='height_lte_22.0', violation_error_message="Height must be less than or equal to 22 inches"),

        ]
    
    def clean(self):

        print("cleaning piece from models.py method")
        # Get the length, width, and height
        length = self.length
        width = self.width
        height = self.height
        
        # compute the size

        # Calculate the size
        size = decimal.Decimal(length * width * height)
        # set to 2 decimal places
        size = size.quantize(decimal.Decimal('0.01'))
        # Set the cleaned data for size
        self.size = size

        # Calculate the price
        # get the price scaling based on the user is a current_staff or current_admin or not
        bisque_temp = self.bisque_temp
        if bisque_temp != 'None':
            # get the price scaling based on the user is a current_staff or current_admin or not
            if self.ghp_user.current_staff or self.ghp_user.current_admin:
                firing_price = decimal.Decimal(STAFF_FIRING_SCALE) * size
            else: 
                firing_price = decimal.Decimal(USER_FIRING_SCALE) * size
            # set to 2 decimal places
            firing_price = firing_price.quantize(decimal.Decimal('0.01'))
        else:
            firing_price = decimal.Decimal(0.00)
        # Set the cleaned data for price
        self.firing_price = firing_price

        # Get the glaze temperature
        glaze_temp = self.glaze_temp
        # Check that the glaze temperature is not None
        if glaze_temp != 'None':
            # Get the price scaling based on the user is a current_staff or current_admin or not
            if self.ghp_user.current_staff or self.ghp_user.current_admin:
                glazing_price = decimal.Decimal(STAFF_GLAZING_SCALE) * size
                glazing_price = glazing_price.quantize(decimal.Decimal('0.01'))
            else:
                glazing_price = decimal.Decimal(USER_GLAZING_SCALE) * size
                glazing_price = glazing_price.quantize(decimal.Decimal('0.01'))
        else:
            glazing_price = decimal.Decimal(0.00)


        # Set the cleaned data for glazing_price
        self.glazing_price = glazing_price
            
            
            
        # Set the new price
        price = glazing_price + firing_price
        # set to 2 decimal places
        price = price.quantize(decimal.Decimal('0.01'))
        # Set the cleaned data for price
        self.price = price



        # Check that the size and price are not negative
        if size < 0:
            self.add_error('size', 'Size must be positive')
        if price < 0:
            self.add_error('price', 'Price must be positive')
        
        if price < MINIMUM_PRICE:
            self.price = decimal.Decimal(MINIMUM_PRICE)
            #self.add_error('price', 'Price must be at least $' + str(MINIMUM_PRICE))
        return self
        # Return the cleaned data
        # return cleaned_data

    def save(self, *args, **kwargs):

        
        # price, glazing_price, and firing_price are calculated in the clean() method
        # so we need to call clean() before saving
        #self = self.clean()

        # check if we are updating or creating a new piece
        PIECE_UPDATING = False

        if self.id:
            self._state.adding = False

        if not self._state.adding:
            PIECE_UPDATING = True
            print("Updating piece")
            # Get the previous piece object
            previous_piece = Piece.objects.get(pk=self.id)
            print("Previous piece image: ", previous_piece.image)
        # if we are not updating, we should get the current date, and increment the ghp_user_piece_id
        # if we are updating, the size should not, and cannot change
        if not PIECE_UPDATING:
            print("Creating a new piece")
            print("Current image: ", self.image)
            self.ghp_user_piece_id = Piece.objects.filter(ghp_user=self.ghp_user).count() + 1
            self.date = timezone.now()

            # Check the size of the piece is correct (length * width * height) up to 2 decimal places
            size_test = self.length * self.width * self.height
            size_test = size_test.quantize(decimal.Decimal('0.01'), rounding=decimal.ROUND_UP)
            try:
                assert np.abs(size_test - self.size) < 0.01
            except AssertionError:
                print("Size is not correct, recalculating")
                print("size_test: " + str(size_test))
                print("self.size: " + str(self.size))
                print("np.abs(size_test - self.size): " + str(np.abs(size_test - self.size)))
                print("type(size_test): " + str(type(size_test)))
                print("type(self.size): " + str(type(self.size)))
                print("type(np.abs(size_test - self.size)): " + str(type(np.abs(size_test - self.size))))
                self.size = size_test

        # Manage firing, glazing and total price, before we save the piece
        # Make sure not to set the glaze or firing price to zero if the user changes from a non-zero value,
        # otherwise if they change back to the original value we will re-charge them.
        if PIECE_UPDATING:
            # 
            if previous_piece.firing_price > 0:
                previously_paid_for_firing = True
            else:
                previously_paid_for_firing = False
            if previous_piece.glazing_price > 0:
                previously_paid_for_glazing = True
            else:
                previously_paid_for_glazing = False
            print("previously_paid_for_firing: " + str(previously_paid_for_firing))
            print("previously_paid_for_glazing: " + str(previously_paid_for_glazing))
            self.glazing_price = np.max([self.glazing_price, previous_piece.glazing_price])
            self.firing_price = np.max([self.firing_price, previous_piece.firing_price])
        # If we are updating, we should not create a ledger entry or change the 
        # glazing_price unless the glaze_temp has changed:
        if PIECE_UPDATING and (
            (previous_piece.glaze_temp == 'None') and (self.glaze_temp != 'None')
            ):
            # Make sure the glaze price + bisque price is at least MINIMUM_PRICE, 
            # and update the price accordingly
            if self.glazing_price < decimal.Decimal(MINIMUM_PRICE):
                self.glazing_price = decimal.Decimal(MINIMUM_PRICE)
                self.price = self.glazing_price + self.firing_price

        # If we are creating a new piece
        if not PIECE_UPDATING:
            # if we are firing and glazing
            if self.glaze_temp != 'None' and self.bisque_temp != 'None':
                # The total price should be at least MINIMUM_PRICE. 
                # if it is less, set the glazing_price and firing_price each to 
                # 1/2 of the MINIMUM_PRICE, and set the total price to MINIMUM_PRICE
                if self.firing_price + self.glazing_price <  decimal.Decimal(MINIMUM_PRICE):
                    self.firing_price =  decimal.Decimal(MINIMUM_PRICE) / 2
                    self.glazing_price =  decimal.Decimal(MINIMUM_PRICE) / 2
                    self.price = self.firing_price + self.glazing_price

            # if we are only firing
            elif self.glaze_temp == 'None' and self.bisque_temp != 'None':
                # The total price should be at least MINIMUM_PRICE. 
                # if it is less, set the firing_price to MINIMUM_PRICE, 
                # and set the total price to MINIMUM_PRICE
                if self.firing_price < decimal.Decimal(MINIMUM_PRICE):
                    self.firing_price = decimal.Decimal(MINIMUM_PRICE)
                    self.price = self.firing_price
            # if we are only glazing
            elif self.glaze_temp != 'None' and self.bisque_temp == 'None':
                # The total price should be at least MINIMUM_PRICE. 
                # if it is less, set the glazing_price to MINIMUM_PRICE, 
                # and set the total price to MINIMUM_PRICE
                if self.glazing_price < decimal.Decimal(MINIMUM_PRICE):
                    self.glazing_price = decimal.Decimal(MINIMUM_PRICE)
                    self.price = self.glazing_price
            # if we are not firing or glazing
            elif self.glaze_temp == 'None' and self.bisque_temp == 'None':
                # This is not allowed, so raise an error
                raise ValidationError("You must pay to either fire or glaze the piece, or both.")


        # Prices have been updated, save the piece for real
        print("saving the piece")
        super().save(*args, **kwargs)  # Call the "real" save() method.
 
        # POST SAVE ACTIONS

        # If we are updating, we should not create a ledger entry unless the glaze_temp has changed:
        if not PIECE_UPDATING:
            print("Creating a ledger entry for a new piece")
            # we are creating a new piece

            # Get/create the ghp_user_transaction_number for this piece
            ghp_user_transaction_number = Ledger.objects.filter(ghp_user=self.ghp_user).count() + 1


            # Either:
            # 1. The piece is being fired and glazed
            # 2. The piece is being fired, but not glazed
            # 3. The piece is not being fired, but is being glazed

            # Handle case 1: The piece is being fired and glazed
            if self.glaze_temp != 'None' and self.bisque_temp != 'None':
                # Create the ledger enter for the bisque+glaze firing fee
                print("Creating ledger entries for bisque and glaze firing fees")
                
                # Check that the price is the firing + glazing price or that the 
                # ~~price is 1.0 because the firing + glazing price is less than 1.0~~
                assert self.price == self.firing_price + self.glazing_price
                    #   or ( (self.price == 1.0) and 
                    #       (self.firing_price + self.glazing_price < 1.0) 
                    #       )
                

                Ledger.objects.create(
                        date = self.date,
                        ghp_user=self.ghp_user,
                        ghp_user_transaction_number=ghp_user_transaction_number,
                        amount= -1 * self.firing_price, # amount is negative because this is a fee
                        transaction_type='auto_bisque_fee',
                        note='Bisque Firing Fee for Piece #' + str(self.ghp_user_piece_id),
                        piece=self
                        )
                
                Ledger.objects.create(
                        date = self.date,
                        ghp_user=self.ghp_user,
                        ghp_user_transaction_number=ghp_user_transaction_number + 1,
                        amount= -1 * self.glazing_price, # amount is negative because this is a fee
                        transaction_type='auto_glaze_fee',
                        note='Glaze Firing Fee for Piece #' + str(self.ghp_user_piece_id),
                        piece=self
                        )
            # Handle case 2: The piece is being fired, but not glazed
            # Only charge the firing price
            elif self.glaze_temp == 'None' and self.bisque_temp != 'None':
                # Create the ledger enter for the bisque firing fee
                print("Creating ledger entry for bisque firing fee")

                # Check that the firing price is the same as the price or the 
                assert self.firing_price == self.price
                    # or ( 
                    #     (self.price == 1.0) 
                    #     and (self.firing_price < 1.0) 
                    #     )
                

                Ledger.objects.create(
                        date = self.date,
                        ghp_user=self.ghp_user,
                        ghp_user_transaction_number=ghp_user_transaction_number,
                        amount= -1 * self.firing_price, # amount is negative because this is a fee
                        transaction_type='auto_bisque_fee',
                        note='Bisque Firing Fee for Piece #' + str(self.ghp_user_piece_id),
                        piece=self
                        )
            # Handle case 3: The piece is not being fired, but is being glazed
            elif self.glaze_temp != 'None' and self.bisque_temp == 'None':
                # Create the ledger enter for the glaze firing fee
                print("Creating ledger entry for Glaze firing fee")

                # Check that the glazing price is the same as the price 
                assert self.glazing_price == self.price, "Glazing price is not the same as the price: " + str(self.glazing_price) + " != " + str(self.price) + " for piece " + str(self.ghp_user_piece_id) + " for user " + str(self.ghp_user)
                    # or (
                    #     (self.price == 1.0)
                    #     and (self.glazing_price < 1.0)
                    #     )
                
                Ledger.objects.create(
                        date = self.date,
                        ghp_user=self.ghp_user,
                        ghp_user_transaction_number=ghp_user_transaction_number,
                        amount= -1 * self.glazing_price, # amount is negative because this is a fee
                        transaction_type='auto_glaze_fee',
                        note='Glaze Firing Fee for Piece #' + str(self.ghp_user_piece_id),
                        piece=self
                        )
            else:
                print('ERROR: You must select a firing temperature for the '\
                'bisque or glaze firing, or both.\n If you do ' \
                'not want to fire or glaze this piece, do not submit it.\n')
                raise ValueError('You must select a firing temperature for the '\
                'bisque or glaze firing, or both.\n If you do ' \
                'not want to fire or glaze this piece, do not submit it.\n')


            # update the last measure date for the user to be the date of this piece
            self.ghp_user.last_measure_date = self.date

        if PIECE_UPDATING:
            # we are updating a piece
            # The user may be only updating the piece notes, description, booleans
            # for whether the piece has been fired or glazed, etc., or they may be
            # trying to pay for glazing for the piece. We need to check for both cases.
            print("Checking if new transactions are needed for piece update...")

            # Check if the glaze_temp has changed from 'None' to something else
            if (not previously_paid_for_glazing) and (previous_piece.glaze_temp == 'None') and (self.glaze_temp != 'None'):
                # The user is trying to pay for glazing for this piece
                print("Creating ledger entry for a new Glaze firing fee")

                # first get a new transaction number
                ghp_user_transaction_number = Ledger.objects.filter(ghp_user=self.ghp_user).count() + 1
                
                # get a date for the ledger object
                ledger_date = timezone.now()

                # We only want to charge the glazing price, not the full price,
                # since the user may have already paid for the bisque firing

                # Create a ledger entry for the glaze firing fee
                Ledger.objects.create(
                        date = ledger_date,
                        ghp_user=self.ghp_user,
                        ghp_user_transaction_number=ghp_user_transaction_number,
                        amount= -1 * self.glazing_price, # amount is negative because this is a fee
                        transaction_type='auto_glaze_fee',
                        note='Glaze Firing Fee for Piece #' + str(self.ghp_user_piece_id),
                        piece=self
                )

                # If the user is now paying for glazing, we need to update the last measure date
                self.ghp_user.last_measure_date = ledger_date

            # Check if the bisque_temp has changed from 'None' to something else
            if (not previously_paid_for_firing) and (previous_piece.bisque_temp == 'None') and (self.bisque_temp != 'None'):
                # 2/11/24: we are going to allow this for now. 

                print("Creating ledger entry for a new Bisque firing fee")

                # first get a new transaction number
                ghp_user_transaction_number = Ledger.objects.filter(ghp_user=self.ghp_user).count() + 1
                
                # get a date for the ledger object
                ledger_date = timezone.now()

                # We only want to charge the glazing price, not the full price,
                # since the user may have already paid for the bisque firing

                # Create a ledger entry for the glaze firing fee
                Ledger.objects.create(
                        date = ledger_date,
                        ghp_user=self.ghp_user,
                        ghp_user_transaction_number=ghp_user_transaction_number,
                        amount= -1 * self.firing_price, # amount is negative because this is a fee
                        transaction_type='auto_bisque_fee',
                        note='Bisque Firing Fee for Piece #' + str(self.ghp_user_piece_id),
                        piece=self
                )

                # If the user is now paying for glazing, we need to update the last measure date
                self.ghp_user.last_measure_date = ledger_date

                # # The user is trying to pay for bisque firing for this piece, 
                # # but the piece has already been glazed, so this is not possible
                # print("ERROR: " + str(self.ghp_user) + " is trying to pay for bisque firing for a piece that has already been glazed")
                # raise ValueError('You cannot pay for bisque firing for a piece that has already been glazed')

                # perhaps we should consider allowing the user to pay for bisque 
                # firing after glaze firing, in case they get confused, and don't 
                # select bisque firing initally. 

        print("FINISHED SAVING PIECE\n\n")

    def __str__(self):
        return str(self.ghp_user) + ' #' + str(self.ghp_user_piece_id) + ' ' \
                + str(self.length) + 'x' + str(self.width) + 'x' \
                + str(self.height) + ' ' + '$' +  str(self.price) + ' ' \
                + str(self.bisque_temp) + ' ' + str(self.glaze_temp) 


class Ledger(models.Model):
    transaction_id = models.AutoField(primary_key=True)
    date = models.DateTimeField()
    ghp_user = models.ForeignKey(GHPUser, models.SET_NULL, null=True)
    ghp_user_transaction_number = models.IntegerField(default= None )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    transaction_type = models.CharField(max_length=100, choices=TRANSACTION_TYPES)

    note = models.CharField(max_length=1000, blank=True)
    piece = models.ForeignKey(Piece, models.SET_NULL, null=True, blank=True)
    # adding 2/10/24
    stripe_session_id = models.CharField(max_length=100, blank=True, null=True)
    class Meta:
        managed = True
        db_table = 'ledger'

    def __str__(self):
        return self.ghp_user.first_name[:1] + '. ' + self.ghp_user.last_name + ' tr. #' + str(self.ghp_user_transaction_number) + ' ' \
                + self.date.strftime(r'%m/%d/%y') + ' ' + self.date.strftime(r'%H:%M:%S') + ' $' + str(self.amount) + ' ' \
                + self.transaction_type + ' (' + self.note + ')'

    def save(self, *args, **kwargs):
        #do_something()
        LEDGER_UPDATING = False
        if not self._state.adding:
            LEDGER_UPDATING = True

        if self.date is None:
            self.date = timezone.now()

        if self.ghp_user_transaction_number is None:
            self.ghp_user_transaction_number = Ledger.objects.filter(ghp_user=self.ghp_user).count() + 1

        if (self.amount is None) or (self.amount == 0):
            print("Amount is None or 0, canceling the ledger save")
            return
        
        super().save(*args, **kwargs)  # Call the "real" save() method.
        
        # Modify user's Account balance by amount, and update Account.last_update
        if not LEDGER_UPDATING:
            if self.ghp_user is not None:
                self.ghp_user.account.balance += self.amount
                self.ghp_user.account.last_update = timezone.now()
                self.ghp_user.account.save()
            else:
                print('No ghp_user for this transaction')
                raise ValueError('No ghp_user for this transaction')
        else:
            print("LEDGER UPDATING")
            # we are only modifying the note on an existing ledger entry
            pass

        # if ghp_user last measure date is < this ledger entry date, update it
        if self.ghp_user is not None:
            if self.ghp_user.last_measure_date is None:
                self.ghp_user.last_measure_date = self.date.date()
                self.ghp_user.save()
            elif self.ghp_user.last_measure_date < self.date.date():
                self.ghp_user.last_measure_date = self.date.date()
                self.ghp_user.save()

