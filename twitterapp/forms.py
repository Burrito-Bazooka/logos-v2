from django import forms

class SiteSetupForm(forms.Form):
    consumer_key = forms.CharField(max_length=200)
    consumer_secret = forms.CharField(max_length=200)
    access_token = forms.CharField(max_length=200)
    token_secret = forms.CharField(max_length=200)
