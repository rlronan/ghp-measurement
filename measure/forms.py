from django import forms
from .models import Piece
import decimal
# class PieceForm(forms.ModelForm):
#     class Meta:
#         model = Piece
#         fields = ['length', 'width', 'height', 'course'] 


class PieceForm(forms.ModelForm):
    class Meta:
        model = Piece
        fields = ['ghp_user', 'ghp_user_piece_id', 'length', 'width', 'height', 'glaze_temp', 'size', 'price']
        #exclude = ['ghp_user', 'ghp_user_piece_id']
    def __init__(self, *args, **kwargs):
        ghp_user = kwargs.pop('ghp_user', None)
        super().__init__(*args, **kwargs)
        self.fields['ghp_user'].widget = forms.HiddenInput()
        self.fields['ghp_user_piece_id'].widget = forms.HiddenInput()
        # Set initial values for ghp_user and ghp_user_piece_id
        self.fields['ghp_user'].initial = ghp_user
        self.fields['ghp_user_piece_id'].initial = Piece.objects.filter(ghp_user=ghp_user).count() + 1
        self.fields['glaze_temp'].initial = 'Cone 10'

        self.fields['length'] = forms.DecimalField(max_digits=5, decimal_places=2, initial=0.0)
        self.fields['length'].widget.attrs['min'] = 0.0
        self.fields['length'].widget.attrs['step'] = 0.25
        self.fields['length'].widget.attrs['value'] = 0.0
      
        self.fields['width'] = forms.DecimalField(max_digits=5, decimal_places=2, initial=0.0)
        self.fields['width'].widget.attrs['min'] = 0.0
        self.fields['width'].widget.attrs['step'] = 0.25
        self.fields['width'].widget.attrs['value'] = 0.0

        self.fields['height'] = forms.DecimalField(max_digits=5, decimal_places=2, initial=0.0)
        self.fields['height'].widget.attrs['min'] = 0.0
        self.fields['height'].widget.attrs['step'] = 0.25
        self.fields['height'].widget.attrs['value'] = 0.0
        
        # Set initial value for size
        if 'length' in self.data and 'width' in self.data and 'height' in self.data:
            length = decimal.Decimal(self.data.get('length'))
            width = decimal.Decimal(self.data.get('width'))
            height = decimal.Decimal(self.data.get('height'))
            size = decimal.Decimal(length * width * height) 
            self.fields['size'].initial = size
        elif self.instance.pk:
            self.fields['size'].initial 
            
        # Set initial value for price
        if 'size' in self.data:
            size = decimal.Decimal(self.data.get('size'))
            price = decimal.Decimal(0.06) * size
            self.fields['price'].initial = price
        elif self.instance.pk:
            self.fields['price'].initial = decimal.Decimal(0.06) * decimal.Decimal(self.instance.size)
        
        if 'glaze_temp' in self.data:
            glaze_temp = self.data.get('glaze_temp')
            if glaze_temp != 'None':
                price = decimal.Decimal(self.data.get('price'))
                price *= 2
                self.fields['price'].initial = price


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
        
        # Get the size and price
        size = cleaned_data.get('size')
        price = cleaned_data.get('price')
        # Check that the size and price are not negative
        if size < 0:
            self.add_error('size', 'Size must be positive')
        if price < 0:
            self.add_error('price', 'Price must be positive')
        
        # Return the cleaned data
        return cleaned_data

