from django.contrib.auth.models import User
from django import forms
from .models import UserProfile
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.hashers import make_password

class UserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

class UserSignupForm(UserCreationForm):
    name = forms.CharField(max_length=100, label='Name')
    address = forms.CharField(max_length=100, label='Address')

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'name', 'address']

    def save(self, commit=True):
        user = super(UserSignupForm, self).save(commit=False)
        user.first_name = self.cleaned_data['name']
        if commit:
            user.save()
            UserProfile.objects.create(user=user, address=self.cleaned_data['address'])
        return user


class SignUpForm(UserCreationForm):
    email = forms.EmailField(max_length=254, help_text='Required. Inform a valid email address.')

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.password = make_password(self.cleaned_data['password1'])  # Mã hoá mật khẩu trước khi lưu
        if commit:
            user.save()
            UserProfile.objects.get_or_create(user=user)
        return user


class UserProfileForm(forms.ModelForm):
    name = forms.CharField(max_length=100, label="Name")
    address = forms.CharField(max_length=100, label="Address")

    class Meta:
        model = UserProfile
        fields = ['name', 'address', 'phone_number']

    def __init__(self, *args, **kwargs):
        super(UserProfileForm, self).__init__(*args, **kwargs)
        if self.instance:
            self.fields['name'].initial = self.instance.name

