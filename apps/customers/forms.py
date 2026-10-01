"""Forms for customers app."""

from django.contrib.auth.forms import UserCreationForm
from django import forms

from .models import User


class UserRegistrationForm(UserCreationForm):
    """Form for user registration with additional fields."""

    email = forms.EmailField(
        max_length=254,
        help_text="Required. Enter a valid email address.",
    )
    first_name = forms.CharField(
        max_length=150,
        required=True,
        help_text="Your first name.",
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        help_text="Your last name.",
    )
    cpf = forms.CharField(
        max_length=14,
        required=True,
        help_text="Brazilian CPF (format: 000.000.000-00)",
    )

    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
            "cpf",
            "password1",
            "password2",
        ]

    def clean_cpf(self):
        """Validate and normalize CPF."""
        import re

        cpf = self.cleaned_data["cpf"]
        # Remove formatting
        cpf = re.sub(r"[^0-9]", "", cpf)
        # Basic validation
        if len(cpf) != 11:
            raise forms.ValidationError("CPF must have 11 digits.")
        return cpf

    def save(self, commit=True):
        """Save the user with additional fields."""
        user = super().save(commit=commit)
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        if commit:
            user.save()
        return user