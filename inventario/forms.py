from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class RegistroForm(UserCreationForm):
    first_name = forms.CharField(label="Nombre", max_length=30, required=True)
    last_name = forms.CharField(label="Apellido", max_length=30, required=True)
    email = forms.EmailField(label="Correo Electrónico", required=True)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'username']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].help_text = ""
        self.fields['password1'].widget.attrs.update({'maxlength': '10'})
        self.fields['password2'].widget.attrs.update({'maxlength': '10'})