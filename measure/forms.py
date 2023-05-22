from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm, PasswordResetForm, SetPasswordForm, AuthenticationForm
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator, EmailValidator, MinLengthValidator
from django.core.exceptions import ValidationError
from .models import Piece, GHPUser, User, Account, Ledger
from django.utils import timezone
from .constants import *
import decimal
# class PieceForm(forms.ModelForm):
#     class Meta:
#         model = Piece
#         fields = ['length', 'width', 'height', 'course'] 


class PieceForm(forms.ModelForm):
    error_css_class = "error"
    required_css_class = "required"
    firing_price_per_cubic_inch = forms.DecimalField(label="firing_price_per_cubic_inch" , max_digits=5, decimal_places=3, initial=0.00)
    firing_price_per_cubic_inch.widget.attrs.update({'class': 'form-control'})
    glazing_price_per_cubic_inch = forms.DecimalField(label="glazing_price_per_cubic_inch" , max_digits=5, decimal_places=3, initial=0.00)
    glazing_price_per_cubic_inch.widget.attrs.update({'class': 'form-control'})
    class Meta:
        model = Piece
        fields = ['ghp_user', 'ghp_user_piece_id', 'length', 'width', 'height', 
                  'glaze_temp', 'size', 'price', 'firing_price', 'glazing_price', 'course_number', 
                  'piece_description', 'glaze_description', 'note', 'image']
        #exclude = ['ghp_user', 'ghp_user_piece_id']
    def __init__(self, *args, **kwargs):
        self.ghp_user = kwargs.pop('ghp_user', None)
        super().__init__(*args, **kwargs)
        self.fields['ghp_user'].widget = forms.HiddenInput(attrs={'readonly': 'readonly'})
        self.fields['ghp_user_piece_id'].widget = forms.HiddenInput(attrs={'readonly': 'readonly'})
        # Set initial values for ghp_user and ghp_user_piece_id
        self.fields['ghp_user'].initial = self.ghp_user
        self.fields['ghp_user_piece_id'].initial = Piece.objects.filter(ghp_user=self.ghp_user).count() + 1

        self.fields['glaze_temp'].initial = 'Cone 10'

        self.fields['length'] = forms.DecimalField(max_digits=5, decimal_places=2, initial=0.0)
        self.fields['length'].widget.attrs['min'] = 0.5
        self.fields['length'].widget.attrs['step'] = 0.5
      
        self.fields['width'] = forms.DecimalField(max_digits=5, decimal_places=2, initial=0.0)
        self.fields['width'].widget.attrs['min'] = 0.5
        self.fields['width'].widget.attrs['step'] = 0.5

        self.fields['height'] = forms.DecimalField(max_digits=5, decimal_places=2, initial=3.0)
        self.fields['height'].widget.attrs['min'] = 3.0
        self.fields['height'].widget.attrs['step'] = 0.5

        # Set initial value for size
        self.fields['size'] = forms.DecimalField(max_digits=10, decimal_places=2, initial=0.00)
        self.fields['price'] = forms.DecimalField(max_digits=10, decimal_places=2, initial=1.00)

        self.fields['firing_price'] = forms.DecimalField(max_digits=10, decimal_places=2, initial=1.00)
        self.fields['glazing_price'] = forms.DecimalField(max_digits=10, decimal_places=2, initial=0.00)


        # Set widget for size field to ReadOnlyInput
        self.fields['size'].widget = forms.TextInput(attrs={'readonly': 'readonly'})
        self.fields['price'].widget = forms.TextInput(attrs={'readonly': 'readonly'})

        self.fields['firing_price'].widget = forms.HiddenInput(attrs={'readonly': 'readonly'})
        self.fields['glazing_price'].widget = forms.HiddenInput(attrs={'readonly': 'readonly'})

        self.fields['course_number'].widget.attrs['placeholder'] = 'e.g. W7'
        self.fields['piece_description'].widget = forms.Textarea(attrs={'rows': 4, 'cols': 40})
        self.fields['piece_description'].widget.attrs['placeholder'] = 'e.g. Very skinny vase with handles and a gash. Planning to paint a face on it later with green wash'

        self.fields['glaze_description'].widget = forms.Textarea(attrs={'rows': 4, 'cols': 40})
        self.fields['glaze_description'].widget.attrs['placeholder'] = 'e.g. Chun Blue splattered over Shino White on the outside, Chun Blue on the inside'

        self.fields['note'].widget = forms.Textarea(attrs={'rows': 4, 'cols': 40})
        self.fields['note'].widget.attrs['placeholder'] = 'e.g. This piece is for my mom\'s birthday'

        self.fields['firing_price_per_cubic_inch'].initial = self.ghp_user.get_price_scale()[0]
        self.fields['glazing_price_per_cubic_inch'].initial = self.ghp_user.get_price_scale()[1]

        self.fields['firing_price_per_cubic_inch'].widget = forms.HiddenInput(attrs={'readonly': 'readonly'})
        self.fields['glazing_price_per_cubic_inch'].widget = forms.HiddenInput(attrs={'readonly': 'readonly'})

        # Set initial values for ghp_user and ghp_user_piece_id



    def clean(self):

        print("Cleaning Piece form")

        # Get the cleaned data
        cleaned_data = super().clean()
        
        # Get the length, width, and height
        length = cleaned_data.get('length')
        width = cleaned_data.get('width')
        height = cleaned_data.get('height')
        # Check that the length, width, and height are not negative
        if length < 0:
            self.add_error('length', 'Length must be positive')
        if width < 0:
            self.add_error('width', 'Width must be positive')
        if height < 0:
            self.add_error('height', 'Height must be positive')
        
        # Round each of the length, width, and height to the nearest 1/2 inch upwards
        length = (decimal.Decimal(2) * length).quantize(decimal.Decimal(1), rounding=decimal.ROUND_UP) / decimal.Decimal(2)
        width = (decimal.Decimal(2) * width).quantize(decimal.Decimal(1), rounding=decimal.ROUND_UP) / decimal.Decimal(2)
        height = (decimal.Decimal(2) * height).quantize(decimal.Decimal(1), rounding=decimal.ROUND_UP) / decimal.Decimal(2)
        
        # Set the cleaned data for length, width, and height
        cleaned_data['length'] = length
        cleaned_data['width'] = width
        cleaned_data['height'] = height

        # Calculate the size
        size = decimal.Decimal(length * width * height)
        # set to 2 decimal places
        size = size.quantize(decimal.Decimal('0.01'))
        # Set the cleaned data for size
        cleaned_data['size'] = size

        # Calculate the price
        # get the price scaling based on the user is a current_staff or current_admin or not
        if self.ghp_user.current_staff or self.ghp_user.current_admin:
            firing_price = decimal.Decimal(STAFF_FIRING_SCALE) * size
        else: 
            firing_price = decimal.Decimal(USER_FIRING_SCALE) * size
        # set to 2 decimal places
        firing_price = firing_price.quantize(decimal.Decimal('0.01'))
        # Set the cleaned data for price
        cleaned_data['firing_price'] = firing_price

        # Get the glaze temperatures
        glaze_temp = cleaned_data.get('glaze_temp')
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
        cleaned_data['glazing_price'] = glazing_price
            
            
            
        # Set the new price
        price = glazing_price + firing_price
        # set to 2 decimal places
        price = price.quantize(decimal.Decimal('0.01'))
        # Set the cleaned data for price
        cleaned_data['price'] = price



        # Check that the size and price are not negative
        if cleaned_data['size'] < 0:
            self.add_error('size', 'Size must be positive')
        if cleaned_data['price'] < 0:
            self.add_error('price', 'Price must be positive')
        
        if cleaned_data['price'] < MINIMUM_PRICE:
            cleaned_data['price'] = decimal.Decimal(MINIMUM_PRICE)
            #self.add_error('price', 'Price must be at least $' + str(MINIMUM_PRICE))
        # Return the cleaned data
        return cleaned_data



class ModifyPieceForm(forms.ModelForm):
    error_css_class = "error"
    required_css_class = "required"
    firing_price_per_cubic_inch = forms.DecimalField(label="firing_price_per_cubic_inch" , max_digits=5, decimal_places=3, initial=0.00)
    firing_price_per_cubic_inch.widget.attrs.update({'class': 'form-control'})
    glazing_price_per_cubic_inch = forms.DecimalField(label="glazing_price_per_cubic_inch" , max_digits=5, decimal_places=3, initial=0.00)
    glazing_price_per_cubic_inch.widget.attrs.update({'class': 'form-control'})
    # piece_id = forms.IntegerField(label="piece_id", initial=0) 
    # piece_id.widget.attrs.update({'class': 'form-control'})
    class Meta:
        model = Piece
        fields = ['ghp_user', 'ghp_user_piece_id',  'length', 'width', 'height', 
                  'glaze_temp', 'size', 'price', 'firing_price', 'glazing_price', 'course_number', 
                  'piece_description', 'glaze_description', 'note', 'image']
        #exclude = ['ghp_user', 'ghp_user_piece_id']
    def __init__(self, *args, **kwargs):
        self.ghp_user = kwargs.pop('ghp_user', None)
        self.piece = kwargs.pop('piece', None)
        super().__init__(*args, **kwargs)
        self.fields['ghp_user'].widget = forms.HiddenInput(attrs={'readonly': 'readonly'})
        self.fields['ghp_user_piece_id'].widget = forms.HiddenInput(attrs={'readonly': 'readonly'})

        self.fields['ghp_user'].initial = self.ghp_user
        self.fields['ghp_user_piece_id'].initial = self.piece.ghp_user_piece_id

        self.fields['glaze_temp'].initial = self.piece.glaze_temp

        self.fields['length'] = forms.DecimalField(max_digits=5, decimal_places=2, initial=self.piece.length)
        self.fields['width'] = forms.DecimalField(max_digits=5, decimal_places=2, initial=self.piece.width)
        self.fields['height'] = forms.DecimalField(max_digits=5, decimal_places=2, initial=self.piece.height)
        self.fields['length'].widget.attrs['readonly'] = 'readonly'
        self.fields['width'].widget.attrs['readonly'] = 'readonly'
        self.fields['height'].widget.attrs['readonly'] = 'readonly'
        # Set initial value for size
        self.fields['size'] = forms.DecimalField(max_digits=10, decimal_places=2, initial=self.piece.size)
        self.fields['size'].widget.attrs['readonly'] = 'readonly'


        # Initial value for price is zero, because the user may not opt to glaze the piece.
        self.fields['price'] = forms.DecimalField(max_digits=5, decimal_places=2, initial=self.piece.price)
        self.fields['price'].widget.attrs['readonly'] = 'readonly'

        self.fields['firing_price'].widget = forms.HiddenInput(attrs={'readonly': 'readonly'})
        self.fields['glazing_price'].widget = forms.HiddenInput(attrs={'readonly': 'readonly'})


        # Set widget for size field to ReadOnlyInput

        self.fields['course_number'].widget.attrs['placeholder'] = 'e.g. W7'
        self.fields['course_number'].initial = self.piece.course_number
        self.fields['course_number'].widget.attrs['readonly'] = 'readonly'

        self.fields['piece_description'].widget = forms.Textarea(attrs={'rows': 4, 'cols': 40})
        self.fields['piece_description'].widget.attrs['placeholder'] = 'e.g. Very skinny vase with handles and a gash. Planning to paint a face on it later with green wash'
        self.fields['piece_description'].initial = self.piece.piece_description

        self.fields['glaze_description'].widget = forms.Textarea(attrs={'rows': 4, 'cols': 40})
        self.fields['glaze_description'].widget.attrs['placeholder'] = 'e.g. Chun Blue splattered over Shino White on the outside, Chun Blue on the inside'
        self.fields['glaze_description'].initial = self.piece.glaze_description


        self.fields['note'].widget = forms.Textarea(attrs={'rows': 4, 'cols': 40})
        self.fields['note'].widget.attrs['placeholder'] = 'e.g. This piece is for my mom\'s birthday'
        self.fields['note'].initial = self.piece.note

        self.fields['firing_price_per_cubic_inch'].initial = self.ghp_user.get_price_scale()[0]
        self.fields['glazing_price_per_cubic_inch'].initial = self.ghp_user.get_price_scale()[1]

        self.fields['firing_price_per_cubic_inch'].widget = forms.HiddenInput(attrs={'readonly': 'readonly'})
        self.fields['glazing_price_per_cubic_inch'].widget = forms.HiddenInput(attrs={'readonly': 'readonly'})

    def clean(self):
        # Get the cleaned data
        print("Cleaning modify piece form")
        cleaned_data = super().clean()

        # Get the length, width, and height
        length = cleaned_data.get('length')
        width = cleaned_data.get('width')
        height = cleaned_data.get('height')
        # Check that the length, width, and height are not negative
        if length < 0:
            self.add_error('length', 'Length must be positive')
        if width < 0:
            self.add_error('width', 'Width must be positive')
        if height < 0:
            self.add_error('height', 'Height must be positive')
        
        # Round each of the length, width, and height to the nearest 1/2 inch upwards
        length = (decimal.Decimal(2) * length).quantize(decimal.Decimal(1), rounding=decimal.ROUND_UP) / decimal.Decimal(2)
        width = (decimal.Decimal(2) * width).quantize(decimal.Decimal(1), rounding=decimal.ROUND_UP) / decimal.Decimal(2)
        height = (decimal.Decimal(2) * height).quantize(decimal.Decimal(1), rounding=decimal.ROUND_UP) / decimal.Decimal(2)
        
        # Set the cleaned data for length, width, and height
        cleaned_data['length'] = length
        cleaned_data['width'] = width
        cleaned_data['height'] = height

        # Calculate the size
        size = decimal.Decimal(length * width * height)
        # set to 2 decimal places
        size = size.quantize(decimal.Decimal('0.01'))
        # Set the cleaned data for size
        cleaned_data['size'] = size

        # Calculate the price
        # get the price scaling based on the user is a current_staff or current_admin or not
        if self.ghp_user.current_staff or self.ghp_user.current_admin:
            firing_price = decimal.Decimal(STAFF_FIRING_SCALE) * size
        else: 
            firing_price = decimal.Decimal(USER_FIRING_SCALE) * size
        # set to 2 decimal places
        firing_price = firing_price.quantize(decimal.Decimal('0.01'))
        # Set the cleaned data for price
        cleaned_data['firing_price'] = firing_price

        # Get the glaze temperature
        glaze_temp = cleaned_data.get('glaze_temp')
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
        cleaned_data['glazing_price'] = glazing_price
            
            
            
        # Set the new price
        price = glazing_price + firing_price
        # set to 2 decimal places
        price = price.quantize(decimal.Decimal('0.01'))
        # Set the cleaned data for price
        cleaned_data['price'] = price



        # Check that the size and price are not negative
        if cleaned_data['size'] < 0:
            self.add_error('size', 'Size must be positive')
        if cleaned_data['price'] < 0:
            self.add_error('price', 'Price must be positive')
        
        if cleaned_data['price'] < MINIMUM_PRICE:
            cleaned_data['price'] = decimal.Decimal(MINIMUM_PRICE)
            #self.add_error('price', 'Price must be at least $' + str(MINIMUM_PRICE))
        # Return the cleaned data
        return cleaned_data
    


class CreateGHPUserForm(UserCreationForm):
    error_css_class = "error"
    required_css_class = "required"
    class Meta:
        model = GHPUser
        fields = ['first_name', 'last_name', 'email', 'username', 'phone_number', 'consent']
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last Name'}),
        }
        # 'username', 'password1', 'password2', 

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['consent'].label = "I agree to the terms of service and privacy policy"
        self.fields['consent'].required = True
        self.fields['consent'].error_messages = {'required': 'You must agree to the terms of service and privacy policy'}
        self.fields['password1'].widget.attrs['placeholder'] = 'Password'
        self.fields['password2'].widget.attrs['placeholder'] = 'Confirm Password'
        self.fields['password1'].widget.attrs['class'] = 'password'
        self.fields['password2'].widget.attrs['class'] = 'password'
        #self.fields['password1'].widget.attrs['autocomplete'] = 'new-password'
        #self.fields['password2'].widget.attrs['autocomplete'] = 'new-password'
        self.fields['email'].widget.attrs['placeholder'] = 'Email'
        
        self.fields['phone_number'].widget.attrs['placeholder'] = 'Phone Number'
        #self.fields['phone_number'].widget.attrs['type'] = 'tel'
        self.fields['phone_number'].widget.attrs['pattern'] = '[0-9]{3}-[0-9]{3}-[0-9]{4}'
        self.fields['phone_number'].widget.attrs['title'] = 'Phone number must be in the format XXX-XXX-XXXX'
        #self.fields['phone_number'].widget.attrs['autocomplete'] = 'tel-national'
        self.fields['phone_number'].widget.attrs['required'] = True
        self.fields['phone_number'].error_messages = {'required': 'Phone number is required'}
        self.fields['phone_number'].help_text = 'Phone number must be in the format XXX-XXX-XXXX'
        #self.fields['phone_number'].validators = [RegexValidator(regex='[0-9]{3}-[0-9]{3}-[0-9]{4}', message='Phone number must be in the format XXX-XXX-XXXX')]
        
        #self.fields['email'].widget.attrs['autocomplete'] = 'email'
        self.fields['email'].widget.attrs['required'] = True
        self.fields['email'].error_messages = {'required': 'Email is required'}
        self.fields['email'].help_text = 'Email is required'
       # self.fields['email'].validators = [EmailValidator(message='Email is invalid')]
        
        #self.fields['first_name'].widget.attrs['autocomplete'] = 'given-name'
        self.fields['first_name'].widget.attrs['required'] = True
        self.fields['first_name'].error_messages = {'required': 'First name is required'}
        self.fields['first_name'].help_text = 'First name is required'
        
        #self.fields['last_name'].widget.attrs['autocomplete'] = 'family-name'
        self.fields['last_name'].widget.attrs['required'] = True
        self.fields['last_name'].error_messages = {'required': 'Last name is required'}
        self.fields['last_name'].help_text = 'Last name is required'
        
        self.fields['password1'].help_text = 'Password must be at least 8 characters long'
        self.fields['password2'].help_text = 'Enter the same password as before, for verification'
        self.fields['password1'].validators = [MinLengthValidator(8, message='Password must be at least 8 characters long')]
        self.fields['password2'].validators = [MinLengthValidator(8, message='Password must be at least 8 characters long')]
        self.fields['password1'].error_messages = {'required': 'Password is required'}
        self.fields['password2'].error_messages = {'required': 'Password is required'}
        self.fields['password1'].required = True
        self.fields['password2'].required = True
        self.fields['password1'].label = 'Password'
        self.fields['password2'].label = 'Confirm Password'

        self.fields['username'].widget = forms.HiddenInput(attrs={'readonly': 'readonly'})
        self.fields['username'].required = False
        self.fields['username'].initial = self.fields['email'].initial
        self.fields['username'].validators = []
        self.fields['username'].error_messages = {}
        self.fields['username'].help_text = ''
        self.fields['username'].label = ''

    
    def clean(self):
        # Get the cleaned data
        cleaned_data = super().clean()
        # Check that the password and confirm password match
        if cleaned_data.get('password1') != cleaned_data.get('password2'):
            self.add_error('password2', 'Passwords do not match')

        cleaned_data['username'] = cleaned_data['email']

        # Return the cleaned data
        return cleaned_data
    

class RefundPieceForm(forms.ModelForm):

    firing_fee_refund = forms.DecimalField(max_digits=10, decimal_places=2)
    firing_fee_refund.widget.attrs['readonly'] = 'readonly'

    firing_fee_check = forms.BooleanField(required=False, initial=True)

    glazing_fee_refund = forms.DecimalField(max_digits=10, decimal_places=2)
    glazing_fee_refund.widget.attrs['readonly'] = 'readonly'
    glazing_fee_check = forms.BooleanField(required=False, initial=True)

    class Meta:
        model = Ledger
        fields = ['ghp_user', 'firing_fee_refund', 'glazing_fee_refund', 'firing_fee_check', 'glazing_fee_check',

                  'amount', 'transaction_type', 'note', ]
    def __init__(self, *args, **kwargs):
        self.ghp_user = kwargs.pop('ghp_user', None)
        piece = kwargs.pop('piece', None)
        ledgers = kwargs.pop('ledgers', None)
        print("ledgers: ", ledgers)
        print("piece: ", piece)
        print("ghp_user: ", self.ghp_user)
        super().__init__(*args, **kwargs)
        
        self.fields['ghp_user'].widget.attrs['readonly'] = 'readonly'
        self.fields['ghp_user'].initial = self.ghp_user

        # self.fields['ghp_user'] = forms.HiddenInput(attrs={'readonly': 'readonly'})
        self.fields['amount'] = forms.DecimalField(max_digits=10, decimal_places=2)
        # Go through the ledgers and get the firing and glazing fees paid
        num_ledgers = len(ledgers)
        print("num_ledgers: ", num_ledgers)
        if num_ledgers == 0:
            # nothing to refund, this should never happen because
            # you should not be able to measure a piece without paying for it, 
            # but just in case, set everything to 0
            self.fields['firing_fee_refund'].initial = 0
            self.fields['glazing_fee_refund'].initial = 0
            self.fields['amount'].initial = 0
        elif num_ledgers == 1:
            # Only one ledger; usually this will be a firing fee + Glazing fee,
            # but it could just a firing or jjust a glazing fee if the piece 
            # was fired outside of the studio
            ledger = ledgers[0]
            glazing_fee = False
            firing_fee = False
            if ledger.transaction_type.lower().find('glaz') != -1:
                glazing_fee = True
            if ledger.transaction_type.lower().find('fir') != -1:
                firing_fee = True
            
            if glazing_fee and firing_fee:
                # get the firing fee and glazing fee from the piece in this case
                # since we don't know the amount of the firing fee or glazing fee
                # although atm (5/22/23) they should be equal
                self.fields['firing_fee_refund'].initial = piece.firing_price
                self.fields['glazing_fee_refund'].initial = piece.glazing_price
                self.fields['amount'].initial = max(piece.firing_price + piece.glazing_price, 1.0)
                if not(self.fields['amount'].initial == piece.price):
                    print("ERROR: The amount of the refund is not equal to the price of the piece")
                    print("piece.price: ", piece.price)
                    print("self.fields['amount'].initial: ", self.fields['amount'].initial)
                    print("piece.firing_price: ", piece.firing_price)
                    print("piece.glazing_price: ", piece.glazing_price)
                    print("ledger.amount: ", -1*ledger.amount)
            elif firing_fee:
                self.fields['firing_fee_refund'].initial = -1*ledger.amount
                self.fields['glazing_fee_refund'].initial = 0
                self.fields['amount'].initial = -1*ledger.amount
                assert(-1*ledger.amount >= 1.0)

            elif glazing_fee:
                self.fields['firing_fee_refund'].initial = 0
                self.fields['glazing_fee_refund'].initial = -1*ledger.amount
                self.fields['amount'].initial = ledger.amount
                assert(-1*ledger.amount >= 1.0)
            else:
                print("ERROR: There is one ledger which does not apear to be a glazing or firing fee")

        elif num_ledgers == 2:
            # Should be one firing fee and one glazing fee;
            # Each ledger should cost at least $1, so the total should be at least $2.0
            ledger1 = ledgers[0]
            ledger2 = ledgers[1]
            if ledger1.transaction_type.lower().find('fir') != -1:
                # ledger1 is a glazing fee
                self.fields['firing_fee_refund'].initial = -1*ledger2.amount
                self.fields['glazing_fee_refund'].initial = -1*ledger1.amount
                self.fields['amount'].initial = -1*ledger1.amount + -1*ledger2.amount
                assert(-1*ledger1.amount >= 1.0)
                assert(-1*ledger2.amount >= 1.0)
                assert(self.fields['amount'].initial >= 2.0)
            elif ledger2.transaction_type.lower().find('fir') != -1:
                # ledger2 is a glazing fee
                self.fields['firing_fee_refund'].initial = -1*ledger1.amount
                self.fields['glazing_fee_refund'].initial = -1*ledger2.amount
                self.fields['amount'].initial = -1*ledger1.amount + -1*ledger2.amount
                assert(-1*ledger1.amount >= 1.0)
                assert(-1*ledger2.amount >= 1.0)

            else:
                print("ERROR: There are two ledgers, but neither is a firing fee")
                self.fields['firing_fee_refund'].initial = 0
                self.fields['glazing_fee_refund'].initial = 0
                self.fields['amount'].initial = piece.price
                assert(self.fields['amount'].initial >= 2.0)

        else:
            print("ERROR: There are more than two ledgers for this piece")
            self.fields['firing_fee_refund'].initial = 0
            self.fields['glazing_fee_refund'].initial = 0
            self.fields['amount'].initial = piece.price
            assert(self.fields['amount'].initial >= 2.0)


            


        self.fields['amount'].widget.attrs['readonly'] = 'readonly'

        self.fields['transaction_type'].initial = 'Refund for piece'


        self.fields['note'].initial = 'Refund for piece: ' + piece.__str__()
        
        # self.fields['piece'].initial = piece
        # self.fields['piece'].widget.attrs['readonly'] = 'readonly'
        # self.fields['piece'].widget.attrs['hidden'] = True

    
    def clean(self):
        # Get the cleaned data
        cleaned_data = super().clean()

        # Get the glazing fee check
        glazing_fee_check = cleaned_data.get('glazing_fee_check')
        glazing_fee_refund = cleaned_data.get('glazing_fee_refund')
        # Get the firing fee check
        firing_fee_check = cleaned_data.get('firing_fee_check')
        firing_fee_refund = cleaned_data.get('firing_fee_refund')

        # Get the amount
        amount = cleaned_data.get('amount')

        # double check that the amount is correct
        # JQuery should have handled this
        if glazing_fee_check and firing_fee_check:
            assert(amount == glazing_fee_refund + firing_fee_refund)
        elif glazing_fee_check:
            assert(amount == glazing_fee_refund)
        elif firing_fee_check:
            assert(amount == firing_fee_refund)
        else:
            print("ERROR: No glazing or firing fee was selected")
            raise ValidationError("You must refund at least one fee")
        # Return the cleaned data
        return cleaned_data
    
    