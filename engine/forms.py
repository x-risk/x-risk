from django import forms
from django.db import models
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Assessment, Topic, Profile


class AssessmentForm(forms.ModelForm):
    # Uncomment for radio buttons.
    #CHOICES = ((True, 'Yes'), (False, 'No'))
    #is_relevant = forms.TypedChoiceField(choices=CHOICES, widget=forms.RadioSelect)

    class Meta:
        model = Assessment
        fields = ['is_relevant', 'topic']


class SignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    email = forms.EmailField(max_length=254)
    institution = forms.CharField(max_length=254)
    educational_attainment = forms.ChoiceField(widget=forms.Select, choices=Profile.EDUCATIONAL_ATTAINMENT_CHOICES)
    topics = forms.ModelMultipleChoiceField(queryset=Topic.objects.all())

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'institution', 'educational_attainment', 'email', 'password1', 'password2', 'topics')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        username = self.cleaned_data.get('username')
        if email and User.objects.filter(email=email).exclude(
            username=username).exists():
            self.add_error('email', 'This email address has already been registered.')
            # raise forms.ValidationError('This email address has already been registered.')
        return email


class UserForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)

    class Meta:
        model = User
        fields = ('first_name', 'last_name',)


class ProfileForm(forms.ModelForm):
    institution = forms.CharField(max_length=254)
    topics = forms.ModelMultipleChoiceField(queryset=Topic.objects.all())

    class Meta:
        model = Profile
        fields = ('institution', 'educational_attainment', 'topics')
