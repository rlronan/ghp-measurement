from django import forms
from .models import Piece
from .constants import *
import decimal
# class PieceForm(forms.ModelForm):
#     class Meta:
#         model = Piece
#         fields = ['length', 'width', 'height', 'course'] 


class PieceForm(forms.ModelForm):
    error_css_class = "error"
    required_css_class = "required"
    class Meta:
        model = Piece
        fields = ['ghp_user', 'ghp_user_piece_id', 'length', 'width', 'height', 
                  'glaze_temp', 'size', 'price', 'course_number', 
                  'piece_description', 'glaze_description', 'note', 'image',]
        #exclude = ['ghp_user', 'ghp_user_piece_id']
    def __init__(self, *args, **kwargs):
        self.ghp_user = kwargs.pop('ghp_user', None)
        super().__init__(*args, **kwargs)
        self.fields['ghp_user'].widget = forms.HiddenInput()
        self.fields['ghp_user_piece_id'].widget = forms.HiddenInput()
        # Set initial values for ghp_user and ghp_user_piece_id
        self.fields['ghp_user'].initial = self.ghp_user
        self.fields['ghp_user_piece_id'].initial = Piece.objects.filter(ghp_user=self.ghp_user).count() + 1

        self.fields['glaze_temp'].initial = 'Cone 10'

        self.fields['length'] = forms.DecimalField(max_digits=5, decimal_places=2, initial=0.5)
        self.fields['length'].widget.attrs['min'] = 0.5
        self.fields['length'].widget.attrs['step'] = 0.5
        self.fields['length'].widget.attrs['value'] = 0.5
      
        self.fields['width'] = forms.DecimalField(max_digits=5, decimal_places=2, initial=0.5)
        self.fields['width'].widget.attrs['min'] = 0.5
        self.fields['width'].widget.attrs['step'] = 0.5
        self.fields['width'].widget.attrs['value'] = 0.5

        self.fields['height'] = forms.DecimalField(max_digits=5, decimal_places=2, initial=3.0)
        self.fields['height'].widget.attrs['min'] = 3.0
        self.fields['height'].widget.attrs['step'] = 0.5
        self.fields['height'].widget.attrs['value'] = 3.0
        


        # Set initial value for size
        self.fields['size'] = forms.DecimalField(max_digits=5, decimal_places=2, initial=0.75)
        self.fields['price'] = forms.DecimalField(max_digits=5, decimal_places=2, initial=1.0)

        # Set widget for size field to ReadOnlyInput
        self.fields['size'].widget = forms.TextInput(attrs={'readonly': 'readonly'})
        self.fields['price'].widget = forms.TextInput(attrs={'readonly': 'readonly'})

    def clean(self):
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
            price = decimal.Decimal(STAFF_FIRING_SCALE) * size
        else: 
            price = decimal.Decimal(USER_FIRING_SCALE) * size
        # set to 2 decimal places
        price = price.quantize(decimal.Decimal('0.01'))
        # Set the cleaned data for price
        cleaned_data['price'] = price

        # Get the glaze temperature
        glaze_temp = cleaned_data.get('glaze_temp')
        # Check that the glaze temperature is not None
        if glaze_temp != 'None':
            if self.ghp_user.current_staff or self.ghp_user.current_admin:
                glaze_price = decimal.Decimal(STAFF_GLAZING_SCALE) * size
                glaze_price = glaze_price.quantize(decimal.Decimal('0.01'))
            else:
                glaze_price = decimal.Decimal(USER_GLAZING_SCALE) * size
                glaze_price = glaze_price.quantize(decimal.Decimal('0.01'))

            # Set the new price
            price = glaze_price + cleaned_data.get('price')
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

