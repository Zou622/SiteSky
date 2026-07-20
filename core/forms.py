from django import forms
from .models import MessageContact


class MessageContactForm(forms.ModelForm):
    website = forms.CharField(
        required=False,
        widget=forms.HiddenInput,
        label="",
    )

    def clean_website(self):
        website = self.cleaned_data.get('website', '').strip()
        if website:
            raise forms.ValidationError("Le formulaire semble avoir été soumis automatiquement.")
        return website

    class Meta:
        model = MessageContact
        fields = ['nom', 'email', 'sujet', 'message']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Votre nom'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@exemple.com'}),
            'sujet': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Sujet'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Votre message', 'rows': 4}),
        }
        error_messages = {
            'nom': {'required': "Ce champ est obligatoire."},
            'email': {
                'required': "Ce champ est obligatoire.",
                'invalid': "Veuillez saisir une adresse email valide.",
            },
            'sujet': {'required': "Ce champ est obligatoire."},
            'message': {'required': "Ce champ est obligatoire."},
        }
from django import forms
from django.core.exceptions import ValidationError
import re

class InfosClientForm(forms.Form):
    nom = forms.CharField(
        label="Nom complet",
        max_length=100,
        error_messages={'required': "Ce champ est obligatoire."}
    )
    telephone = forms.CharField(
        label="Téléphone",
        max_length=9,
        error_messages={'required': "Ce champ est obligatoire.", 'invalid': "Veuillez saisir un numéro valide."}
    )
    email = forms.EmailField(
        label="Email",
        required=False,
        error_messages={'invalid': "Veuillez saisir une adresse email valide."}
    )
    adresse = forms.CharField(
        label="Adresse de livraison",
        widget=forms.Textarea,
        required=False,
        error_messages={'required': "Ce champ est obligatoire."}
    )
    choix_retrait = forms.ChoiceField(
        label="Mode de retrait",
        choices=[('livraison', 'Livraison à domicile'), ('agence', 'Retrait en agence')],
        widget=forms.RadioSelect,
        error_messages={'required': "Ce champ est obligatoire."}
    )

    def clean_telephone(self):
        tel = self.cleaned_data.get('telephone', '').strip()
        if not re.match(r'^(61|62|65|66)[0-9]{7}$', tel):
            raise ValidationError("Veuillez saisir un numéro valide")
        return tel

    # L'adresse détaillée est optionnelle (même pour la livraison). Le support commercial pourra contacter le client si nécessaire.
    def clean_adresse(self):
        adresse = self.cleaned_data.get('adresse', '').strip()
        return adresse


class WifiTicketPurchaseForm(forms.Form):
    nom = forms.CharField(
        label="Nom complet",
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        error_messages={'required': "Ce champ est obligatoire."}
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        error_messages={
            'required': "Ce champ est obligatoire.",
            'invalid': "Veuillez saisir une adresse email valide.",
        }
    )
    telephone = forms.CharField(label="Téléphone (optionnel)", max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if not email:
            raise ValidationError("L'email est requis pour l'envoi des identifiants.")
        return email