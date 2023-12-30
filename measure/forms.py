from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm, PasswordResetForm, SetPasswordForm, AuthenticationForm
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator, EmailValidator, MinLengthValidator
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from .models import Piece, GHPUser, User, Account, Ledger
from django.utils import timezone
from .constants import *
import decimal

import gettext
_ = gettext.gettext
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
        fields = ['ghp_user', 'ghp_user_piece_id', 'piece_location',
                  'length', 'width', 'height', 'bisque_temp',
                  'glaze_temp', 'size', 'price', 
                  'firing_price', 'glazing_price', 
                  'course_number', 'note', 
                  'image'] #'piece_description', 'glaze_description', 
        #exclude = ['ghp_user', 'ghp_user_piece_id']
    def __init__(self, *args, **kwargs):
        self.ghp_user = kwargs.pop('ghp_user', None)
        self.user_balance = kwargs.pop('user_balance', None)
        self.ghp_user_location = self.ghp_user.get_location()

        print("user balance: ", self.user_balance)
        print("user location: ", self.ghp_user_location)
        super().__init__(*args, **kwargs)
        self.fields['ghp_user'].widget = forms.HiddenInput(attrs={'readonly': 'readonly'})
        self.fields['ghp_user_piece_id'].widget = forms.HiddenInput(attrs={'readonly': 'readonly'})
        # Set initial values for ghp_user and ghp_user_piece_id
        self.fields['ghp_user'].initial = self.ghp_user
        self.fields['ghp_user_piece_id'].initial = Piece.objects.filter(ghp_user=self.ghp_user).count() + 1

        self.fields['bisque_temp'].initial = 'Cone 06'
        self.fields['glaze_temp'].initial = 'Cone 10'


        self.fields['piece_location'] = forms.ChoiceField(choices=LOCATION_CHOICES, initial=self.ghp_user_location)
        
        if self.fields['piece_location'].initial == 'Greenwhich':
            self.fields['bisque_temp'] = forms.ChoiceField(choices=BISQUE_TEMPS_GREENWICH, initial='Cone 06')
            self.fields['glaze_temp'] = forms.ChoiceField(choices=GLAZE_TEMPS_GREENWICH, initial='Cone 10')
        elif self.fields['piece_location'].initial == 'Chelsea':
            self.fields['bisque_temp'] = forms.ChoiceField(choices=BISQUE_TEMPS_CHELSEA, initial='Cone 06')
            self.fields['glaze_temp'] = forms.ChoiceField(choices=GLAZE_TEMPS_CHELSEA, initial='Cone 10')
    

        self.fields['length'] = forms.DecimalField(max_digits=5, decimal_places=1)#, initial=0.0)
        self.fields['length'].widget.attrs['min'] = 0.5
        self.fields['length'].widget.attrs['step'] = 0.5
      
        self.fields['width'] = forms.DecimalField(max_digits=5, decimal_places=1)#, initial=0.0)
        self.fields['width'].widget.attrs['min'] = 0.5
        self.fields['width'].widget.attrs['step'] = 0.5

        self.fields['height'] = forms.DecimalField(max_digits=5, decimal_places=1)#, initial=3.0)
        self.fields['height'].widget.attrs['min'] = 3.0
        self.fields['height'].widget.attrs['step'] = 0.5

        # Set initial value for size
        self.fields['size'] = forms.DecimalField(max_digits=10, decimal_places=2, initial=0.00)
        self.fields['price'] = forms.DecimalField(max_digits=10, decimal_places=2, initial=1.00)

        self.fields['firing_price'] = forms.DecimalField(max_digits=10, decimal_places=2, initial=1.00)
        self.fields['glazing_price'] = forms.DecimalField(max_digits=10, decimal_places=2, initial=0.00)


        # Set widget for size field to ReadOnlyInput
        self.fields['size'].widget = forms.HiddenInput(attrs={'readonly': 'readonly'})
        self.fields['price'].widget = forms.TextInput(attrs={'readonly': 'readonly'})

        self.fields['firing_price'].widget = forms.HiddenInput(attrs={'readonly': 'readonly'})
        self.fields['glazing_price'].widget = forms.HiddenInput(attrs={'readonly': 'readonly'})

        self.fields['course_number'].widget.attrs['placeholder'] = 'e.g. W7'
        # self.fields['piece_description'].widget = forms.Textarea(attrs={'rows': 4, 'cols': 30})
        # self.fields['piece_description'].widget.attrs['placeholder'] = 'e.g. Very skinny vase with handles and a gash. Planning to paint a face on it later with green wash'

        # self.fields['glaze_description'].widget = forms.Textarea(attrs={'rows': 4, 'cols': 30})
        # self.fields['glaze_description'].widget.attrs['placeholder'] = 'e.g. Chun Blue splattered over Shino White on the outside, Chun Blue on the inside'

        self.fields['note'].widget = forms.Textarea(attrs={'rows': 4, 'cols': 30})
        self.fields['note'].widget.attrs['placeholder'] = 'Chun Blue splattered over Shino White on the outside, Chun Blue on the inside'

        self.fields['firing_price_per_cubic_inch'].initial = self.ghp_user.get_price_scale()[0]
        self.fields['glazing_price_per_cubic_inch'].initial = self.ghp_user.get_price_scale()[1]

        self.fields['firing_price_per_cubic_inch'].widget = forms.HiddenInput(attrs={'readonly': 'readonly'})
        self.fields['glazing_price_per_cubic_inch'].widget = forms.HiddenInput(attrs={'readonly': 'readonly'})

        self.fields['image'] = forms.ImageField(required=False)
        ###self.fields['image'].widget.attrs['accept'] = 'image/*'
        #self.user_balance = self.ghp_user_acount.balance
        # set the user balance to the current user balance
#        self.fields['user_balance'].initial=self.ghp_user.get_balance()
        # self.fields['user_balance'].widget = forms.TextInput(attrs={'readonly': 'readonly'})


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

        # Get the bisque temperature
        bisque_temp = cleaned_data.get('bisque_temp')
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
        print(self.user_balance, cleaned_data['price'], self.user_balance - cleaned_data['price'])
        if self.user_balance - cleaned_data['price'] < -25:
            raise ValidationError(
                _("You cannot measure a piece that will bring your account balance below -$25.00. Please add money to your account before measuring."),
                code="balance_too_low")

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
        fields = ['ghp_user', 'ghp_user_piece_id', 'piece_location', 'length', 'width', 'height', 
                  'glaze_temp', 'size', 'price', 'firing_price', 'glazing_price', 'course_number', 
                 'note', 'image']
        #exclude = ['ghp_user', 'ghp_user_piece_id']
    def __init__(self, *args, **kwargs):
        self.ghp_user = kwargs.pop('ghp_user', None)
        self.piece = kwargs.pop('piece', None)
        self.ghp_user_location = self.ghp_user.get_location()

        ##self.piece_image = kwargs.pop('piece_image', None)
        super().__init__(*args, **kwargs)
        self.fields['ghp_user'].widget = forms.HiddenInput(attrs={'readonly': 'readonly'})
        self.fields['ghp_user_piece_id'].widget = forms.HiddenInput(attrs={'readonly': 'readonly'})

        self.fields['ghp_user'].initial = self.ghp_user
        self.fields['ghp_user_piece_id'].initial = self.piece.ghp_user_piece_id

        self.fields['piece_location'].initial  = self.piece.piece_location
        self.fields['bisque_temp'].initial = self.piece.bisque_temp
        self.fields['glaze_temp'].initial = self.piece.glaze_temp

        self.fields['length'] = forms.DecimalField(max_digits=5, decimal_places=2, initial=self.piece.length)
        self.fields['width'] = forms.DecimalField(max_digits=5, decimal_places=2, initial=self.piece.width)
        self.fields['height'] = forms.DecimalField(max_digits=5, decimal_places=2, initial=self.piece.height)
        self.fields['length'].widget.attrs['readonly'] = 'readonly'
        self.fields['width'].widget.attrs['readonly'] = 'readonly'
        self.fields['height'].widget.attrs['readonly'] = 'readonly'
        # Set initial value for size
        # self.fields['size'] = forms.DecimalField(max_digits=10, decimal_places=2, initial=self.piece.size)
        # self.fields['size'].widget.attrs['readonly'] = 'readonly'
        self.fields['size'].widget = forms.HiddenInput(attrs={'readonly': 'readonly'})


        # Initial value for price is zero, because the user may not opt to glaze the piece.
        self.fields['price'] = forms.DecimalField(max_digits=5, decimal_places=2, initial=self.piece.price)
        self.fields['price'].widget.attrs['readonly'] = 'readonly'

        self.fields['firing_price'].widget = forms.HiddenInput(attrs={'readonly': 'readonly'})
        self.fields['glazing_price'].widget = forms.HiddenInput(attrs={'readonly': 'readonly'})


        # Set widget for size field to ReadOnlyInput

        self.fields['course_number'].widget.attrs['placeholder'] = 'e.g. W7'
        self.fields['course_number'].initial = self.piece.course_number
        self.fields['course_number'].widget.attrs['readonly'] = 'readonly'

        # self.fields['piece_description'].widget = forms.Textarea(attrs={'rows': 4, 'cols': 30})
        # self.fields['piece_description'].widget.attrs['placeholder'] = 'e.g. Very skinny vase with handles and a gash. Planning to paint a face on it later with green wash'
        # self.fields['piece_description'].initial = self.piece.piece_description

        # self.fields['glaze_description'].widget = forms.Textarea(attrs={'rows': 4, 'cols': 30})
        # self.fields['glaze_description'].widget.attrs['placeholder'] = 'e.g. Chun Blue splattered over Shino White on the outside, Chun Blue on the inside'
        # self.fields['glaze_description'].initial = self.piece.glaze_description


        self.fields['note'].widget = forms.Textarea(attrs={'rows': 4, 'cols': 30})
        self.fields['note'].widget.attrs['placeholder'] = 'e.g. Very skinny vase with handles and a gash. Glazed with Chun Blue splattered over Shino White on the outside, Chun Blue on the inside.'
        self.fields['note'].initial = self.piece.note

        self.fields['firing_price_per_cubic_inch'].initial = self.ghp_user.get_price_scale()[0]
        self.fields['glazing_price_per_cubic_inch'].initial = self.ghp_user.get_price_scale()[1]

        self.fields['firing_price_per_cubic_inch'].widget = forms.HiddenInput(attrs={'readonly': 'readonly'})
        self.fields['glazing_price_per_cubic_inch'].widget = forms.HiddenInput(attrs={'readonly': 'readonly'})
        if self.piece.image:
            print("found self image: ", self.piece.image)
            self.fields['image'] = forms.ImageField(required=False, initial=self.piece.image)
        else:
            self.fields['image'] = forms.ImageField(required=False)

    def clean(self):
        # Get the cleaned data
        print("Cleaning modify piece form")
        cleaned_data = super().clean()
        
        original_image = self.piece.image
        print("original image: ", original_image)
        new_image = cleaned_data.get('image')
        print("new image: ", new_image)
        
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

        # Get the bisque temperature
        bisque_temp = cleaned_data.get('bisque_temp')
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

        # self.add_error('user_balance_too_low', 'You cannot measure a piece that will bring your account balance below -$25.00. Please pay your balance before measuring this piece.')
        
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
        
        #self.fields['phone_number'].widget.attrs['placeholder'] = 'Phone Number'
        #self.fields['phone_number'].widget.attrs['type'] = 'tel'
        #self.fields['phone_number'].widget.attrs['pattern'] = '[0-9]{3}-[0-9]{3}-[0-9]{4}'
        #self.fields['phone_number'].widget.attrs['title'] = 'Phone number must be in the format XXX-XXX-XXXX'
        #self.fields['phone_number'].widget.attrs['autocomplete'] = 'tel-national'
        #self.fields['phone_number'].widget.attrs['required'] = True
        #self.fields['phone_number'].error_messages = {'required': 'Phone number is required'}
        #self.fields['phone_number'].help_text = 'Phone number must be in the format XXX-XXX-XXXX'
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
    
# TODO: Really should create a better way to manage transaction_types!
class RefundPieceForm(forms.ModelForm):

    firing_fee_refund = forms.DecimalField(max_digits=10, decimal_places=2)
    firing_fee_refund.widget.attrs['readonly'] = 'readonly'
    firing_fee_check = forms.BooleanField(required=False, initial=True)

    firing_fee_refunded = forms.BooleanField(required=False, initial=False)

    glazing_fee_refund = forms.DecimalField(max_digits=10, decimal_places=2)
    glazing_fee_refund.widget.attrs['readonly'] = 'readonly'
    glazing_fee_check = forms.BooleanField(required=False, initial=True)

    glazing_fee_refunded = forms.BooleanField(required=False, initial=False)


    class Meta:
        model = Ledger
        fields = ['ghp_user', 'firing_fee_refund', 'firing_fee_refunded',  
                  'glazing_fee_refund', 'glazing_fee_refunded','firing_fee_check', 
                  'glazing_fee_check', 'piece',
                  'amount', 'transaction_type', 'note', ]
    def __init__(self, *args, **kwargs):
        self.ghp_refund_user = kwargs.pop('ghp_user', None)
        piece = kwargs.pop('piece', None)
        ledgers = kwargs.pop('ledgers', None)
        print("ledgers: ", ledgers)
        print("piece: ", piece)
        print("ghp_user: ", self.ghp_refund_user)
        super().__init__(*args, **kwargs)

        self.fields['ghp_user'].widget = forms.HiddenInput(attrs={'readonly': 'readonly'})
        self.fields['ghp_user'].initial = self.ghp_refund_user

        self.fields['amount'] = forms.DecimalField(max_digits=10, decimal_places=2)
        self.fields['amount'].widget.attrs['readonly'] = 'readonly'
        
        self.fields['piece'].widget = forms.HiddenInput(attrs={'readonly': 'readonly'})
        self.fields['piece'].initial = piece
        
        
        self.fields['transaction_type'].widget = forms.HiddenInput(attrs={'readonly': 'readonly'})
        # self.fields['transaction_type'].initial = 'Refund for piece'


        self.fields['note'].initial = 'Refund for piece: ' + piece.__str__()
        self.fields['note'].widget = forms.Textarea(attrs={'rows': 4, 'cols': 20})

        glazing_fee = False
        firing_fee = False
        self.fields['firing_fee_refunded'].initial = False
        self.fields['glazing_fee_refunded'].initial = False

        self.fields['firing_fee_refund'].initial = 0
        self.fields['glazing_fee_refund'].initial = 0

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

        else:
            for ledger in ledgers:
                print("ledger: ", ledger)
                if ledger.transaction_type.lower() == 'auto_bisque_fee':
                    print("found a bisque fee of amount: ", ledger.amount)
                    firing_fee = True
                    self.fields['firing_fee_refund'].initial += -1*ledger.amount
                    print("firing_fee_refund: ", self.fields['firing_fee_refund'].initial)
                
                elif ledger.transaction_type.lower() == 'auto_glaze_fee':
                    print("found a glaze fee of amount: ", ledger.amount)
                    glazing_fee = True
                    self.fields['glazing_fee_refund'].initial += -1*ledger.amount
                
                elif ledger.transaction_type.lower() == 'auto_refund_bisque_fee':
                    print("found a bisque fee refund of amount: ", ledger.amount)
                    self.fields['firing_fee_refunded'].initial = True
                    self.fields['firing_fee_refund'].initial += -1*ledger.amount
                
                elif ledger.transaction_type.lower() == 'auto_refund_glaze_fee':
                    print("found a glaze fee refund of amount: ", ledger.amount)
                    self.fields['glazing_fee_refunded'].initial = True
                    self.fields['glazing_fee_refund'].initial += -1*ledger.amount
                
                elif glazing_fee and firing_fee:
                    raise ValidationError("ERROR: The ledger is both a glazing fee and a firing fee")
                    # this should not be possible anymore with 1 ledger. 
                
                else:
                    print("ERROR: There is at least one ledger which does not apear to be a glazing or firing fee")
                print("firing_fee_refunded: ", self.fields['firing_fee_refunded'].initial)

        if self.fields['firing_fee_refunded'].initial:
            assert firing_fee == True, 'ERROR: The firing fee was refunded, but there is no firing fee ledger'
        
            if self.fields['firing_fee_refund'].initial != 0:
                # This should never happen, but handle numerical errors in case
                assert self.fields['firing_fee_refund'].initial <= 0.1, \
                       "Error: firing fee was previously refunded, but the firing fee and refund amount do not match"
                self.fields['firing_fee_refund'].initial = 0
        
        if self.fields['glazing_fee_refunded'].initial:
            assert glazing_fee == True, 'ERROR: The glazing fee was refunded, but there is no glazing fee ledger'
        
            if self.fields['glazing_fee_refund'].initial != 0:
                # This should never happen, but handle numerical errors in case
                assert self.fields['glazing_fee_refund'].initial <= 0.1, \
                       "Error: glazing fee was previously refunded, but the glazing fee and refund amount do not match"
                self.fields['glazing_fee_refund'].initial = 0
        
        if firing_fee and not self.fields['firing_fee_refunded'].initial:
            assert self.fields['firing_fee_refund'].initial >= 0.5, \
                   'Error: There is a firing fee which was not refunded, \
                    but the refund amount is not at least $0.50'
        
        
        if glazing_fee and not self.fields['glazing_fee_refunded'].initial:
            assert self.fields['glazing_fee_refund'].initial >= 0.5, \
                   'Error: There is a glazing fee which was not refunded, \
                    but the refund amount is not at least $0.50'
        
        
        self.fields['amount'].initial = self.fields['firing_fee_refund'].initial + self.fields['glazing_fee_refund'].initial
        self.fields['amount'].widget.attrs['readonly'] = 'readonly'


        if self.fields['firing_fee_check'] and firing_fee >= 0.5:
            self.fields['transaction_type'].initial = 'auto_refund_bisque_fee'
        elif self.fields['glazing_fee_check'] and glazing_fee >= 0.5:
            self.fields['transaction_type'].initial = 'auto_refund_glaze_fee'
        else:
            self.fields['transaction_type'].initial = 'auto_refund_bisque_fee'


    def clean(self):
        # Get the cleaned data
        print("in clean():")
        cleaned_data = super().clean()

        # Get the glazing fee check
        glazing_fee_check = cleaned_data.get('glazing_fee_check')
        glazing_fee_refund = cleaned_data.get('glazing_fee_refund')
        # Get the firing fee check
        firing_fee_check = cleaned_data.get('firing_fee_check')
        firing_fee_refund = cleaned_data.get('firing_fee_refund')

        # Get the amount
        amount = cleaned_data.get('amount')

        if firing_fee_check and glazing_fee_check:
            # want to refund both fees
            if ((firing_fee_refund > 0) and (glazing_fee_refund > 0)):
                # we need to create two ledgers actually, one for each refund type
                # so split off the glazing fee refund into a separate ledger
                # and then use this ledger to create the firing fee refund
                glazing_fee_ledger = Ledger(
                    ghp_user = cleaned_data.get('ghp_user'),
                    amount = glazing_fee_refund,
                    transaction_type = 'auto_refund_glaze_fee',
                    note = cleaned_data.get('note'),
                    piece = cleaned_data.get('piece')
                )
                glazing_fee_ledger.save()

                # This ledger is the firing fee ledger, so just set the amount to 
                # the firing fee refund, and the transaction_type to auto_refund_bisque_fee,
                # and keep the note and piece the same
                cleaned_data['amount'] = firing_fee_refund
                cleaned_data['transaction_type'] = 'auto_refund_bisque_fee'
                #cleaned_data['note'] = cleaned_data.get('note') 
        elif firing_fee_check:
            # want to refund firing fee only
            cleaned_data['transaction_type'] = 'auto_refund_bisque_fee'
            cleaned_data['amount'] = firing_fee_refund
        elif glazing_fee_check:
            # want to refund glazing fee only
            cleaned_data['transaction_type'] = 'auto_refund_glaze_fee'
            cleaned_data['amount'] = glazing_fee_refund
        else:
            print("ERROR: No glazing or firing fee was selected")
            raise ValidationError("You must refund at least one fee. To Cance, go back to the previous page.")
        # Return the cleaned data
        print("Transaction type: ", cleaned_data.get('transaction_type'))


        return cleaned_data
    

class AddCreditForm(forms.ModelForm):

    account_balance = forms.DecimalField(max_digits=10, decimal_places=2, required=False)
    account_balance.widget.attrs['readonly'] = 'readonly'

    class Meta:
        model = Ledger
        fields = ['ghp_user', 'amount', 'transaction_type', 'note', 'account_balance']

    def __init__(self, *args, **kwargs):
        ghp_user = kwargs.pop('ghp_user')
        ghp_user_account = kwargs.pop('ghp_user_account')
        super().__init__(*args, **kwargs)
        
        self.fields['ghp_user'].initial = ghp_user
        self.fields['ghp_user'].widget = forms.HiddenInput(attrs={'readonly': 'readonly'})

        self.fields['amount'].initial = 0

        self.fields['transaction_type'].initial = 'manual_gh_add_misc_credit'
        self.fields['transaction_type'].widget = forms.HiddenInput(attrs={'readonly': 'readonly'})

        self.fields['note'].initial = 'Manual credit added by GHP staff'
        self.fields['note'].widget = forms.Textarea(attrs={'rows': 4, 'cols': 40})
        
        self.fields['account_balance'].initial = ghp_user_account.balance

    def clean(self):
        # Get the cleaned data
        cleaned_data = super().clean()
        # if the amount is < 0, then change the transaction to to 'manual_gh_add_misc_charge'
        if cleaned_data['amount'] == 0:
            raise ValidationError("You must enter a value other than 0")
        elif cleaned_data.get('amount') < 0:
            cleaned_data['transaction_type'] = 'manual_gh_add_misc_charge'
        elif cleaned_data.get('amount') > 0:
            cleaned_data['transaction_type'] = 'manual_gh_add_misc_credit'

        return cleaned_data