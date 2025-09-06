from django import forms
from django.contrib.auth.forms import AuthenticationForm
from App.models import Customer, Product, Bidnow,User ,AboutUs, SiteSetting, ContactUs

# class LoginForm(AuthenticationForm):
#     username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control','placeholder': 'Username' }))
#     password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control','placeholder': 'Password' }))
# class log(forms.models):
#     class Meta:
#         model =User
#         fields = ['email','phone_number','password1','password2']

class CustomerProfileForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields =  ['locality','city']
        widgets ={
            # 'first_name':forms.TextInput(attrs={'class':'form-control'}),
            # 'last_name':forms.TextInput(attrs={'class':'form-control'}),
            'locality':forms.TextInput(attrs={'class':'form-control'}),
            'city':forms.TextInput(attrs={'class':'form-control'}),  
        }
  

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = '__all__'



class BidForm(forms.Form):
    bid_amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        label="Your Bid Amount (Rs.)",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your bid amount',
            'min': '1'
        })
    )



class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(
        max_length=254,
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'you@example.com',
            'id': 'email',
        }),
        label='Email address'
    )

class AboutUsForm(forms.ModelForm):
    class Meta:
        model = AboutUs
        fields = '__all__'
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'})
        }


class SiteSettingForm(forms.ModelForm):
    class Meta:
        model = SiteSetting
        fields = '__all__'
        widgets = {
            'office_description': forms.TextInput(attrs={'class': 'form-control'}),
            'office_phone': forms.NumberInput(attrs={'class': 'form-control'}),
            'office_address': forms.TextInput(attrs={'class': 'form-control'}),
            'office_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'facebook': forms.URLInput(attrs={'class': 'form-control'}),
            'x': forms.URLInput(attrs={'class': 'form-control'}),
            'instagram': forms.URLInput(attrs={'class': 'form-control'}),
            'linkedin': forms.URLInput(attrs={'class': 'form-control'}),
            'iframe': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean_office_phone(self):
        phone = self.cleaned_data.get('office_phone')
        if phone and len(str(phone)) > 11:
            raise forms.ValidationError("Phone number cannot be longer than 11 digits")
        return phone


class ContactUsForm(forms.ModelForm):
    class Meta:
        model = ContactUs
        fields = '__all__'
