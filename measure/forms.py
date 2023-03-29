from django import forms
from .models import Piece

# class PieceForm(forms.ModelForm):
#     class Meta:
#         model = Piece
#         fields = ['length', 'width', 'height', 'course'] 


class PieceForm(forms.ModelForm):
    class Meta:
        model = Piece
        fields = ['ghp_user', 'ghp_user_piece_id', 'length', 'width', 'height', 'size', 'price']
        #exclude = ['ghp_user', 'ghp_user_piece_id']
    def __init__(self, *args, **kwargs):
        ghp_user = kwargs.pop('ghp_user', None)
        super().__init__(*args, **kwargs)
        self.fields['ghp_user'].widget = forms.HiddenInput()
        self.fields['ghp_user_piece_id'].widget = forms.HiddenInput()
        # Set initial values for ghp_user and ghp_user_piece_id
        self.fields['ghp_user'].initial = ghp_user
        self.fields['ghp_user_piece_id'].initial = Piece.objects.filter(ghp_user=ghp_user).count() + 1
        
        # Set initial value for size
        if 'length' in self.data and 'width' in self.data and 'height' in self.data:
            length = self.data.get('length')
            width = self.data.get('width')
            height = self.data.get('height')
            size = float(length) * float(width) * float(height)
            self.fields['size'].initial = size
            #self.cleaned_data['size'] = size
        elif self.instance.pk:
            self.fields['size'].initial 
            #self.cleaned_data['size'] =  self.instance.length * self.instance.width * self.instance.height
            
        # Set initial value for price
        if 'size' in self.data:
            size = self.data.get('size')
            price = 0.06 * float(size)
            #self.cleaned_data['price'] = price
            self.fields['price'].initial = price
        elif self.instance.pk:
            self.fields['price'].initial = 0.06 * self.instance.size
            #self.cleaned_data['price'] = 0.06 * self.instance.size            
        # Set widget for size field to ReadOnlyInput
        self.fields['size'].widget = forms.TextInput(attrs={'readonly': 'readonly'})
        self.fields['price'].widget = forms.TextInput(attrs={'readonly': 'readonly'})
