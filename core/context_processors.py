from django.db import models
from .models import Logo,Categorie
import os

def logo_context(request):
    logo = Logo.objects.first()
    telephone = os.environ.get('TELEPHONE_COMMERCIAL', '')
    whatsapp_phone = telephone.replace('+', '') if telephone else ''
    return {
        'logo': logo,
        'email_commercial': os.environ.get('EMAIL_COMMERCIAL', ''),
        'telephone_commercial': telephone,
        'whatsapp_phone': whatsapp_phone,
        'facebook_url': os.environ.get('FACEBOOK_URL', ''),
        'twitter_url': os.environ.get('TWITTER_URL', ''),
        'linkedin_url': os.environ.get('LINKEDIN_URL', ''),
    }

def menu_categories(request):
    equipement = Categorie.objects.filter(nom__iexact="Equipement").first()
    accessoire = Categorie.objects.filter(nom__iexact="Accessoire").first()
    return {
        'equipement_categories': equipement.sous_categories.all() if equipement else [],
        'accessoire_categories': accessoire.sous_categories.all() if accessoire else [],
    }

def panier_count(request):
    from .models import Panier, PanierItem
    if request.user.is_authenticated:
        panier, created = Panier.objects.get_or_create(user=request.user)
        count = PanierItem.objects.filter(panier=panier).aggregate(total=models.Sum('quantite'))['total'] or 0
        return {'panier_count': count}
    else:
        # For anonymous users, count items from session cart
        cart = request.session.get('cart', {})
        count = sum(int(v) for v in cart.values())
        return {'panier_count': count}

def site_settings(request):
    """Passe les paramètres de settings importants au template de manière sûre."""
    from django.conf import settings
    return {
        'hide_product_prices': getattr(settings, 'HIDE_PRODUCT_PRICES', False),
        'recaptcha_site_key': getattr(settings, 'RECAPTCHA_SITE_KEY', ''),
        'recaptcha_enabled': bool(getattr(settings, 'RECAPTCHA_SITE_KEY', '') and getattr(settings, 'RECAPTCHA_SECRET_KEY', '')),
    }

# Google OAuth context removed (no longer used)