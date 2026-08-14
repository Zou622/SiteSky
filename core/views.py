from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db import models
from django.core.mail import send_mail, EmailMessage, EmailMultiAlternatives
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.utils.html import strip_tags
from django.conf import settings
from django.urls import reverse
from django.db.models import Sum
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string

import json
import os
import time
import urllib.parse
import urllib.request
from email.mime.image import MIMEImage


from .forms import MessageContactForm, InfosClientForm
from .models import (
    Actualite, QuickBlock, Faq, Forfait, Produit, Panier, PanierItem,
    Categorie, SousCategorie, ZoneCouverture, Commune, Agence,
    DemandeSouscription, Order, OrderItem, Logo, WifiTicketType, WifiTicket
)


def conditions_generales(request):
    """Return the terms & conditions fragment for modal loading."""
    return render(request, 'core/conditions_generales.html')


# sign_out removed: authentication is disabled for public site


def accueil(request):
    # Nettoyer le flag de session si présent
    if 'just_logged_in' in request.session:
        del request.session['just_logged_in']

    quick_blocks = QuickBlock.objects.all().order_by('ordre')
    latest_news = Actualite.objects.order_by('-date_pub')[:6]
    bons_plans_forfaits = Forfait.objects.filter(is_bon_plan=True)[:3]
    bons_plans_equipements = Produit.objects.filter(is_bon_plan=True, quantite__gt=0)[:3] 
    regions = ZoneCouverture.objects.all()
    communes = Commune.objects.all()
    zones_count = regions.count()
    return render(request, 'core/accueil.html', {
        'quick_blocks': quick_blocks,
        'latest_news': latest_news,
        'bons_plans_forfaits': bons_plans_forfaits,
        'bons_plans_equipements': bons_plans_equipements,
        "regions": regions,
        "communes": communes,
        "zones_count": zones_count,
    })

def blog(request):
    actualites = Actualite.objects.all().order_by('-date_pub')
    return render(request, 'core/blog.html', {'actualites': actualites})

def zone_couverture(request):
    from .models import ZoneCouverture
    zones = ZoneCouverture.objects.prefetch_related('communes').all()
    return render(request, 'core/zone_couverture.html', {'zones': zones})

def _verify_recaptcha(response_token):
    secret_key = os.environ.get('RECAPTCHA_SECRET_KEY') or getattr(settings, 'RECAPTCHA_SECRET_KEY', '')
    if not secret_key or not response_token:
        return False

    payload = urllib.parse.urlencode({
        'secret': secret_key,
        'response': response_token,
    }).encode('utf-8')

    try:
        request_data = urllib.request.Request(
            'https://www.google.com/recaptcha/api/siteverify',
            data=payload,
            method='POST',
        )
        with urllib.request.urlopen(request_data, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
        return result.get('success', False)
    except Exception:
        return False


def _is_contact_rate_limited(request):
    last_submit = request.session.get('contact_last_submission')
    now = time.time()
    if last_submit and now - last_submit < 12:
        return True
    request.session['contact_last_submission'] = now
    return False


def contact(request):
    if request.method == 'POST':
        form = MessageContactForm(request.POST)
        if _is_contact_rate_limited(request):
            form.add_error(None, "Veuillez patienter quelques secondes avant de renvoyer votre message.")
        elif form.is_valid():
            recaptcha_response = request.POST.get('g-recaptcha-response', '')
            if not _verify_recaptcha(recaptcha_response):
                form.add_error(None, "Veuillez confirmer que vous n'êtes pas un robot.")
            else:
                message = form.save()
                # Envoi d’un email stylisé à l'adresse définie dans .env (EMAIL_COMMERCIAL)
                recipient = os.environ.get('EMAIL_COMMERCIAL') or getattr(settings, 'DEFAULT_FROM_EMAIL', None)
                context = {
                    'message': message,
                }
                if recipient:
                    envoyer_email_avec_logo(
                        request=request,
                        sujet=f"Nouveau message de contact : {message.sujet}",
                        template_html='emails/contact_commercial.html',
                        template_txt='emails/contact_commercial.txt',
                        context=context,
                        destinataire=recipient,
                    )
                messages.success(request, "Votre message a bien été envoyé !")
                return redirect('contact')
    else:
        form = MessageContactForm()
    return render(request, 'core/contact.html', {'form': form})

def qui_sommes_nous(request):
    return render(request, 'core/qui_sommes_nous.html')

def mentions_legales(request):
    return render(request, 'core/mentions_legales.html')

def faq(request):
    faqs = Faq.objects.prefetch_related('steps__images').order_by('ordre')
    return render(request, 'core/faq.html', {'faqs': faqs})

def _get_session_cart(request):
    """Return session cart dict mapping produit_id (str) -> quantite (int)."""
    return request.session.setdefault('cart', {})


def _save_session_cart(request, cart):
    request.session['cart'] = cart
    request.session.modified = True


def ajouter_au_panier(request, produit_id):
    """
    Ajoute une quantité au panier de l'utilisateur.
    Accepte q en querystring (GET) ou POST.
    Valide et clamp la quantité entre 1 et produit.quantite.
    Retourne {'success': True, 'panier_count': <int>} ou {'success': False, 'error': ...}
    """
    produit = get_object_or_404(Produit, pk=produit_id)

    # Récupère la quantité demandée (GET ?q= ou POST 'q')
    q = request.GET.get('q') or request.POST.get('q') or '1'
    try:
        q = int(q)
    except (ValueError, TypeError):
        q = 1
    if q < 1:
        q = 1

    if produit.quantite <= 0:
        return JsonResponse({'success': False, 'error': "Produit indisponible."}, status=400)

    q = min(q, produit.quantite)

    if request.user.is_authenticated:
        panier, _ = Panier.objects.get_or_create(user=request.user)
        panier_item, created = PanierItem.objects.get_or_create(panier=panier, produit=produit, defaults={'quantite': q})
        if not created:
            # additionne en respectant le stock max
            old_qty = panier_item.quantite
            new_qty = min(produit.quantite, panier_item.quantite + q)
            # Vérifier si la quantité a effectivement augmenté
            if new_qty == old_qty:
                return JsonResponse({'success': False, 'error': 'Stock maximum atteint pour ce produit.'}, status=400)
            panier_item.quantite = new_qty
            panier_item.save(update_fields=['quantite'])

        # Compte total d'articles (somme des quantités)
        total_q = PanierItem.objects.filter(panier=panier).aggregate(total=Sum('quantite'))['total'] or 0
        return JsonResponse({'success': True, 'panier_count': int(total_q)})
    else:
        cart = _get_session_cart(request)
        key = str(produit.id)
        current = int(cart.get(key, 0))
        new_qty = min(produit.quantite, current + q)
        # Vérifier si la quantité a effectivement augmenté
        if new_qty == current:
            return JsonResponse({'success': False, 'error': 'Stock maximum atteint pour ce produit.'}, status=400)
        cart[key] = new_qty
        _save_session_cart(request, cart)
        total_q = sum(int(v) for v in cart.values())
        return JsonResponse({'success': True, 'panier_count': int(total_q)})

def retirer_du_panier(request, item_id):
    # For authenticated users item_id is PanierItem id; for anonymous treat as produit id
    if request.user.is_authenticated:
        PanierItem.objects.filter(id=item_id, panier__user=request.user).delete()
        return redirect('panier')
    else:
        cart = _get_session_cart(request)
        key = str(item_id)
        if key in cart:
            del cart[key]
            _save_session_cart(request, cart)
        return redirect('panier')

def changer_quantite(request, item_id):
    # For authenticated users item_id is PanierItem id
    if request.user.is_authenticated:
        item = get_object_or_404(PanierItem, id=item_id, panier__user=request.user)
        produit = item.produit
        if request.method == "POST":
            quantite = int(request.POST.get("quantite", 1))
            if quantite > produit.quantite:
                quantite = produit.quantite
            if quantite > 0:
                item.quantite = quantite
                item.save()
            else:
                item.delete()
        return redirect('panier')
    else:
        # For anonymous users item_id is produit id
        produit = get_object_or_404(Produit, id=item_id)
        if request.method == "POST":
            quantite = int(request.POST.get("quantite", 1))
            if quantite > produit.quantite:
                quantite = produit.quantite
            cart = _get_session_cart(request)
            if quantite > 0:
                cart[str(produit.id)] = quantite
            else:
                cart.pop(str(produit.id), None)
            _save_session_cart(request, cart)
        return redirect('panier')

def vider_panier(request):
    if request.user.is_authenticated:
        panier, _ = Panier.objects.get_or_create(user=request.user)
        panier.items.all().delete()
    else:
        request.session.pop('cart', None)
    return redirect('panier')

def voir_panier(request):
    items = []
    total = 0
    if request.user.is_authenticated:
        panier, created = Panier.objects.get_or_create(user=request.user)
        for item in panier.items.all():
            items.append({
                'id': item.id,
                'produit': item.produit,
                'quantite': item.quantite,
                'total_ligne': item.produit.prix_ttc * item.quantite,
            })
        total = sum(i['total_ligne'] for i in items)
        return render(request, 'core/panier.html', {'items': items, 'total': total, 'panier': panier})
    else:
        cart = _get_session_cart(request)
        produit_ids = [int(k) for k in cart.keys()]
        produits = Produit.objects.filter(id__in=produit_ids)
        produits_map = {p.id: p for p in produits}
        for pid, qty in cart.items():
            p = produits_map.get(int(pid))
            if not p:
                continue
            total_ligne = p.prix_ttc * int(qty)
            items.append({
                'id': p.id,
                'produit': p,
                'quantite': int(qty),
                'total_ligne': total_ligne,
            })
            total += total_ligne
        return render(request, 'core/panier.html', {'items': items, 'total': total, 'panier': None})

def mes_commandes(request):
    """
    Placeholder view - user order history disabled.
    This view is no longer accessible publicly.
    """
    return redirect('accueil')

def forfaits(request):
    forfaits = Forfait.objects.all()
    regions = ZoneCouverture.objects.all()  # On récupère toutes les régions
    communes = Commune.objects.all()
    return render(request, "core/forfaits.html", {
        "forfaits": forfaits,
        "regions": regions,
        "communes": communes,
    })
# Exemple dans views.py
def equipements(request):
    categories = Categorie.objects.prefetch_related('sous_categories__produits').all()
    return render(request, 'core/equipements.html', {'categories': categories})

def sous_categorie_detail(request, id):
    sous_categorie = SousCategorie.objects.prefetch_related('produits').get(id=id)
    produits = sous_categorie.produits.all()
    return render(request, 'core/sous_categorie_detail.html', {
        'sous_categorie': sous_categorie,
        'produits': produits,
    })

def menu_categories(request):
    equipement_categories = Categorie.objects.filter(nom__iexact="Équipement").first()
    accessoire_categories = Categorie.objects.filter(nom__iexact="Accessoire").first()
    return {
        'equipement_categories': equipement_categories.sous_categories.all() if equipement_categories else [],
        'accessoire_categories': accessoire_categories.sous_categories.all() if accessoire_categories else [],
    }

def produit_detail(request, id):
    produit = Produit.objects.get(id=id)
    # Traitement des caractéristiques
    caracteristiques = []
    if produit.caracteristiques:
        for ligne in produit.caracteristiques.splitlines():
            if ':' in ligne:
                nom, valeur = ligne.split(':', 1)
                caracteristiques.append((nom.strip(), valeur.strip()))
            else:
                caracteristiques.append((ligne.strip(), ''))
    return render(request, 'core/produit_detail.html', {
        'produit': produit,
        'caracteristiques': caracteristiques,
    })


from django.shortcuts import render, redirect
from .models import Forfait, ZoneCouverture, Commune

from django.shortcuts import render, redirect
from .models import Forfait, ZoneCouverture, Commune

def souscription_form(request, forfait_id):
    forfait = get_object_or_404(Forfait, id=forfait_id)
    if request.method == "POST":
        # accepte region OR region_id pour compatibilité
        region_id = request.POST.get("region") or request.POST.get("region_id")
        commune_id = request.POST.get("commune") or request.POST.get("commune_id")
        zone = ZoneCouverture.objects.filter(id=region_id).first() if region_id else None
        commune = Commune.objects.filter(id=commune_id, zone_id=region_id).first() if commune_id else None
        # Si la zone ou commune n'est pas valide, on affiche quand même le formulaire
        # en laissant les champs région/commune vides.
        regions = ZoneCouverture.objects.all()
        communes = Commune.objects.all()
        return render(request, "core/souscription_form.html", {
            "forfait": forfait,
            "zone": zone if zone and commune else None,
            "commune": commune if zone and commune else None,
            "regions": regions,
            "communes": communes,
        })
      # GET
    regions = ZoneCouverture.objects.all()
    communes = Commune.objects.all()
    return render(request, "core/souscription_form.html", {
        "forfait": forfait,
        "regions": regions,
        "communes": communes,
    })
import re
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from .models import DemandeSouscription
from django.core.mail import send_mail

# ...existing code...
def finaliser_souscription(request):
    if request.method != "POST":
        return redirect("forfaits")

    forfait_id = (request.POST.get("forfait_id") or "").strip()
    region_id = (request.POST.get("region_id") or request.POST.get("region") or "").strip()
    commune_id = (request.POST.get("commune_id") or request.POST.get("commune") or "").strip()
    nom = (request.POST.get("nom") or "").strip()
    telephone = (request.POST.get("telephone") or "").strip()
    email = (request.POST.get("email") or "").strip()
    accepte_cgv = request.POST.get("accepte_cgv") == "on"  # Checkbox POST envoie "on" si cochée

    erreurs = []

    # Vérifications basiques
    if not all([forfait_id, region_id, commune_id, nom, telephone]):
        erreurs.append("Tous les champs obligatoires doivent être remplis.")

    # Vérifier l'acceptation des CGV
    if not accepte_cgv:
        erreurs.append("Vous devez accepter les conditions générales pour continuer.")

    if forfait_id and not forfait_id.isdigit():
        erreurs.append("Identifiant de forfait invalide.")
    if region_id and not region_id.isdigit():
        erreurs.append("Identifiant de région invalide.")
    if commune_id and not commune_id.isdigit():
        erreurs.append("Identifiant de commune invalide.")

    if erreurs:
        regions = ZoneCouverture.objects.all()
        communes = Commune.objects.all()
        forfait = Forfait.objects.filter(id=int(forfait_id)).first() if forfait_id.isdigit() else None
        return render(request, "core/souscription_form.html", {
            "erreurs": erreurs,
            "forfait": forfait,
            "regions": regions,
            "communes": communes,
        })

    # Récupération sécurisée des objets
    try:
        forfait = Forfait.objects.get(id=int(forfait_id))
    except (Forfait.DoesNotExist, ValueError):
        erreurs.append("Forfait introuvable.")

    try:
        zone = ZoneCouverture.objects.get(id=int(region_id))
    except (ZoneCouverture.DoesNotExist, ValueError):
        erreurs.append("Zone introuvable.")

    try:
        commune = Commune.objects.get(id=int(commune_id), zone_id=int(region_id))
    except (Commune.DoesNotExist, ValueError):
        erreurs.append("Commune introuvable pour la région sélectionnée.")

    if erreurs:
        regions = ZoneCouverture.objects.all()
        communes = Commune.objects.all()
        return render(request, "core/souscription_form.html", {
            "erreurs": erreurs,
            "forfait": forfait if 'forfait' in locals() else None,
            "regions": regions,
            "communes": communes,
        })

    # Validation téléphone et email
    pattern = r'^(61|62|65|66)[0-9]{7}$'
    if not re.match(pattern, telephone):
        erreurs.append("Numéro de téléphone guinéen invalide.")
    if email:
        try:
            validate_email(email)
        except ValidationError:
            erreurs.append("Adresse email invalide.")

    if erreurs:
        return render(request, "core/souscription_form.html", {
            "erreurs": erreurs,
            "forfait": forfait,
            "zone": zone,
            "commune": commune,
        })

    # Enregistrement
    demande = DemandeSouscription.objects.create(
        nom=nom,
        telephone=telephone,
        email=email,
        forfait=forfait,
        zone=zone,
        commune=commune,
        statut="EN_ATTENTE",
        commercial=None,
        note_interne="",
    )

    # Email au commercial (HTML)
    # préparer URL et flag pour logo (inline CID si le fichier existe)
    logo_fs_path = os.path.join(settings.MEDIA_ROOT, 'logos', 'New_logo.jpg')
    logo_url = request.build_absolute_uri('/media/logos/New_logo.jpg')
    logo_exists = os.path.exists(logo_fs_path)

    context_commercial = {
        'nom': nom,
        'telephone': telephone,
        'email': email,
        'forfait': forfait.nom,
        'zone': zone.region,
        'commune': commune.nom,
        'logo_url': logo_url,
        'logo_cid': logo_exists,
    }

    html_commercial = render_to_string('emails/souscription_commercial.html', context_commercial)
    text_commercial = strip_tags(html_commercial)

    email_commercial = EmailMultiAlternatives(
        subject=f"🔔 NOUVELLE SOUSCRIPTION : {forfait.nom}",
        body=text_commercial,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[os.environ['EMAIL_COMMERCIAL']],
    )
    email_commercial.attach_alternative(html_commercial, "text/html")
    # Attacher le logo en inline (CID) si disponible
    if logo_exists:
        try:
            with open(logo_fs_path, 'rb') as f:
                img = MIMEImage(f.read())
                img.add_header('Content-ID', '<logo>')
                img.add_header('Content-Disposition', 'inline', filename='New_logo.jpg')
                email_commercial.attach(img)
        except Exception:
            pass
    email_commercial.send(fail_silently=False)

    # Email au client (HTML)
    if email:
        context_client = {
            'nom': nom,
            'telephone': telephone,
            'email': email,
            'forfait': forfait.nom,
            'zone': zone.region,
            'commune': commune.nom,
            'logo_url': logo_url,
            'logo_cid': logo_exists,
        }
        html_client = render_to_string('emails/souscription_client.html', context_client)
        text_client = strip_tags(html_client)

        email_client = EmailMultiAlternatives(
            subject=f"Confirmation de votre souscription - {forfait.nom}",
            body=text_client,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email],
        )
        email_client.attach_alternative(html_client, "text/html")
        # Attacher le logo en inline (CID) si disponible
        if logo_exists:
            try:
                with open(logo_fs_path, 'rb') as f:
                    img = MIMEImage(f.read())
                    img.add_header('Content-ID', '<logo>')
                    img.add_header('Content-Disposition', 'inline', filename='New_logo.jpg')
                    email_client.attach(img)
            except Exception:
                pass
        email_client.send(fail_silently=False)

    return render(request, "core/souscription_confirmation.html", {
        "nom": nom,
        "forfait": forfait,
    })

# ...existing code...
from django.utils.crypto import get_random_string

def commande_infos_client(request):
    # Charger les items du panier (DB ou session)
    items = []
    total = 0
    
    if request.user.is_authenticated:
        panier, _ = Panier.objects.get_or_create(user=request.user)
        items_db = PanierItem.objects.filter(panier=panier)
        for item in items_db:
            items.append({
                'produit': item.produit,
                'quantite': item.quantite,
                'total_ligne': item.produit.prix_ttc * item.quantite,
            })
        total = sum(i['total_ligne'] for i in items)
    else:
        # Session cart pour anonyme
        cart = _get_session_cart(request)
        produit_ids = [int(k) for k in cart.keys()]
        produits = Produit.objects.filter(id__in=produit_ids)
        produits_map = {p.id: p for p in produits}
        for pid, qty in cart.items():
            p = produits_map.get(int(pid))
            if not p:
                continue
            total_ligne = p.prix_ttc * int(qty)
            items.append({
                'produit': p,
                'quantite': int(qty),
                'total_ligne': total_ligne,
            })
            total += total_ligne

    regions = ZoneCouverture.objects.all()
    communes = Commune.objects.all()

    if request.method == "POST":
        form = InfosClientForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            # récupérer region et commune sélectionnées
            region_id = request.POST.get('region_id')
            commune_id = request.POST.get('commune_id')
            region_obj = None
            commune_obj = None
            # si livraison, region+commune requis
            if data.get('choix_retrait') == 'livraison':
                if not region_id:
                    form.add_error(None, "Veuillez sélectionner la ville (région).")
                if not commune_id:
                    form.add_error(None, "Veuillez sélectionner la commune.")
            # valider existence en base si fournis
            if region_id:
                try:
                    region_obj = ZoneCouverture.objects.get(id=int(region_id))
                except (ZoneCouverture.DoesNotExist, ValueError):
                    form.add_error(None, "Ville invalide.")
            if commune_id:
                try:
                    commune_obj = Commune.objects.get(id=int(commune_id))
                except (Commune.DoesNotExist, ValueError):
                    form.add_error(None, "Commune invalide.")

            if not form.errors:
                # stocker infos + libellés région/commune
                data['region_id'] = region_obj.id if region_obj else None
                data['region'] = region_obj.region if region_obj else None
                data['commune_id'] = commune_obj.id if commune_obj else None
                data['commune'] = commune_obj.nom if commune_obj else None
                # adresse détaillée déjà dans data['adresse']
                request.session['commande_infos'] = data
                return redirect('commande_confirmation')
    else:
        form = InfosClientForm()

    return render(request, "core/commande_infos_client.html", {
        "form": form,
        "items": items,
        "total": total,
        "regions": regions,
        "communes": communes,
    })

from django.db import transaction
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from django.template.loader import render_to_string
from django.utils import timezone

def commande_confirmation(request):
    # Récupération du panier selon l'authentification
    items_list = []
    total = 0
    
    if request.user.is_authenticated:
        panier, _ = Panier.objects.get_or_create(user=request.user)
        items_list = list(panier.items.all())
        total = sum(item.produit.prix_ttc * item.quantite for item in items_list)
    else:
        cart = _get_session_cart(request)
        produit_ids = [int(k) for k in cart.keys()]
        produits = Produit.objects.filter(id__in=produit_ids)
        produits_map = {p.id: p for p in produits}
        
        class SessionItem:
            def __init__(self, produit, quantite):
                self.produit = produit
                self.quantite = quantite
        
        for pid, qty in cart.items():
            p = produits_map.get(int(pid))
            if p:
                items_list.append(SessionItem(p, int(qty)))
                total += p.prix_ttc * int(qty)
    
    infos = request.session.get('commande_infos')
    
    if not infos:
        return redirect('commande_infos_client')

    erreurs = []
    agences = Agence.objects.all() if infos.get('choix_retrait') == 'agence' else None

    if request.method == "POST":
        try:
            with transaction.atomic():
                # Génération référence
                date_str = timezone.now().strftime('%Y%m%d')
                count = Order.objects.filter(
                    date_commande__date=timezone.now().date()
                ).count() + 1
                reference = f"CMD-{date_str}-{count:04d}"

                # Création commande
                order = Order.objects.create(
                    reference=reference,
                    client=request.user if request.user.is_authenticated else None,
                    nom=infos['nom'],
                    email=infos['email'],
                    telephone=infos['telephone'],
                    mode_reception=infos['choix_retrait'],
                    agence_id=request.POST.get('agence_id'),
                    adresse_livraison=infos.get('adresse'),
                    commune_id=infos.get('commune_id'),
                    montant_total=total,
                    statut='en_attente'  # Statut initial
                )
                # S'assurer que l'instance a bien un PK avant d'accéder aux relations
                order.refresh_from_db()

                # Création items sans toucher au stock
                for item in items_list:
                    OrderItem.objects.create(
                        commande=order,
                        produit=item.produit,
                        quantite=item.quantite,
                        prix_unitaire=item.produit.prix_ttc,
                        total_ligne=item.produit.prix_ttc * item.quantite
                    )

                # Emails au client ET au commercial
                context = {
                    'order': order,
                    'items': order.items.all(),
                    'infos': infos,
                    'hide_product_prices': getattr(settings, 'HIDE_PRODUCT_PRICES', False),
                }
                
                # Email au client
                if order.mode_reception == 'agence':
                    template_html_client = 'emails/commande_retrait_agence.html'
                    template_txt_client = 'emails/commande_retrait_agence.txt'
                else:
                    template_html_client = 'emails/commande_livraison.html'
                    template_txt_client = 'emails/commande_livraison.txt'
                
                envoyer_email_avec_logo(
                    request=request,
                    sujet=f'Confirmation de votre commande {order.reference}',
                    template_html=template_html_client,
                    template_txt=template_txt_client,
                    context=context,
                    destinataire=order.email
                )
                
                # Email au commercial
                context_commercial = {
                    'order': order,
                    'items': order.items.all(),
                    'infos': infos,
                    'hide_product_prices': getattr(settings, 'HIDE_PRODUCT_PRICES', False),
                }
                
                envoyer_email_avec_logo(
                    request=request,
                    sujet=f'🔔 NOUVELLE COMMANDE : {order.reference}',
                    template_html='emails/commande_commercial.html',
                    template_txt='emails/commande_commercial.txt',
                    context=context_commercial,
                    destinataire=os.environ.get('EMAIL_COMMERCIAL', 'contact@skyconnect-sa.com')
                )

                # Vider panier
                if request.user.is_authenticated:
                    panier, _ = Panier.objects.get_or_create(user=request.user)
                    panier.items.all().delete()
                else:
                    # Pour utilisateurs anonymes, vider la session
                    if 'cart' in request.session:
                        del request.session['cart']
                
                if 'commande_infos' in request.session:
                    del request.session['commande_infos']

                request.session['derniere_commande'] = {
                    'reference': order.reference,
                    'total': float(order.montant_total),
                    'mode': order.mode_reception,
                    'agence_nom': order.agence.nom if order.agence else None,
                }

                return redirect('commande_succes')

        except Exception as e:
            print(f"Erreur : {str(e)}")
            erreurs.append(f"Erreur : {str(e)}")
            return render(request, "core/commande_confirmation.html", {
                "infos": infos,
                "items": items_list,
                "total": total,
                "agences": agences,
                "erreurs": erreurs,
            })

    return render(request, "core/commande_confirmation.html", {
        "infos": infos,
        "items": items_list,
        "total": total,
        "agences": agences,
        "erreurs": erreurs,
    })
def commande_succes(request):
    # Ici tu peux afficher le reçu, les instructions, etc.
    return render(request, "core/commande_succes.html")

def commande_detail(request, order_id):
    """
    Placeholder view - detailed order view disabled.
    This view is no longer accessible publicly.
    """
    return redirect('accueil')

def changer_statut_commande(request, order_id):
    """
    Placeholder view - status change disabled for public users.
    This view is only accessible via the admin.
    """
    return JsonResponse({'error': 'Non autorisé'}, status=403)

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from email.mime.image import MIMEImage
from django.conf import settings
import os
from .models import Logo  # Assurez-vous que c'est le bon modèle

from django.core.mail import EmailMultiAlternatives
from email.mime.image import MIMEImage
from django.conf import settings
import os

def envoyer_email_avec_logo(request, sujet, template_html, template_txt, context, destinataire):
    # Récupérer le dernier logo
    logo = Logo.objects.last()
    
    # Créer le message
    msg = EmailMultiAlternatives(
        subject=sujet,
        body=render_to_string(template_txt, context),
        from_email=None,
        to=[destinataire]
    )
    
    # Si un logo existe, l'intégrer dans l'email
    if logo and logo.image:
        # Lire le fichier image
        image_path = logo.image.path
        with open(image_path, 'rb') as f:
            logo_data = f.read()
        
        # Créer l'image attachée avec un Content-ID
        logo_img = MIMEImage(logo_data)
        logo_img.add_header('Content-ID', '<logo>')
        msg.attach(logo_img)
        
        # Ajouter l'URL CID au contexte
        context['logo_cid'] = 'cid:logo'
    
    # Ajouter la version HTML
    html_content = render_to_string(template_html, context)
    msg.attach_alternative(html_content, "text/html")
    
    # Envoyer
    msg.send()


def tickets(request):
    """Page d'achat de tickets WiFi hotspot.

    Affiche les différents types de tickets disponibles (1h, 2h, etc.)
    et permet aux utilisateurs d'acheter des tickets.
    """
    from .models import WifiTicketType

    # Récupérer tous les types de tickets actifs
    ticket_types = WifiTicketType.objects.filter(is_active=True)

    context = {
        'ticket_types': ticket_types,
    }

    return render(request, 'core/tickets.html', context)

def _sync_ticket_to_radius(ticket):
    """Write a newly purchased ticket directly to radcheck so it works instantly."""
    from django.db import connections
    username = ticket.identifiant
    session_timeout = ticket.ticket_type.duree_minutes * 60

    try:
        cursor = connections['radius'].cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM radcheck WHERE username = %s",
            [username]
        )
        already_exists = cursor.fetchone()[0] > 0

        if not already_exists:
            # Password in radcheck
            cursor.execute(
                "INSERT INTO radcheck (username, attribute, op, value) VALUES (%s, 'Cleartext-Password', ':=', %s)",
                [username, ticket.mot_de_passe]
            )
            # Session-Timeout in radcheck (hard enforcement - FreeRADIUS will reject after this)
            cursor.execute(
                "INSERT INTO radcheck (username, attribute, op, value) VALUES (%s, 'Session-Timeout', ':=', %s)",
                [username, str(session_timeout)]
            )
            # Session-Timeout in radreply (tells MikroTik how long to allow the session)
            cursor.execute(
                "INSERT INTO radreply (username, attribute, op, value) VALUES (%s, 'Session-Timeout', ':=', %s)",
                [username, str(session_timeout)]
            )
            # Limite totale de session (sqlcounter)
            cursor.execute(
                "INSERT INTO radcheck (username, attribute, op, value) "
                "VALUES (%s, 'Max-All-Session', ':=', %s)",
                [username, str(session_timeout)]
            )
            # Acct-Interim-Interval: MikroTik sends accounting updates every 60s
            # This allows FreeRADIUS to track live sessions and enforce limits
            cursor.execute(
                "INSERT INTO radreply (username, attribute, op, value) VALUES (%s, 'Acct-Interim-Interval', ':=', '60')",
                [username]
            )
            connections['radius'].commit()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"RADIUS sync failed for {username}: {e}")

def acheter_ticket(request, ticket_type_id):
    """Affiche le formulaire d'achat pour un type de ticket et le traite."""
    ticket_type = get_object_or_404(WifiTicketType, id=ticket_type_id, is_active=True)
    from .forms import WifiTicketPurchaseForm

    if request.method == 'POST':
        form = WifiTicketPurchaseForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            # Générer identifiant et mot de passe
            identifiant = f"ticket_{get_random_string(length=8, allowed_chars='0123456789')}"
            mot_de_passe = get_random_string(length=10)
            date_expiration = None

            ticket = WifiTicket.objects.create(
                ticket_type=ticket_type,
                identifiant=identifiant,
                mot_de_passe=mot_de_passe,
                date_expiration=date_expiration,
            )
            # Sync to FreeRADIUS immediately after purchase
            _sync_ticket_to_radius(ticket)

            # Préparer le contexte pour l'email
            context = {
                'nom': data.get('nom'),
                'email': data.get('email'),
                'telephone': data.get('telephone'),
                'ticket': ticket,
                'ticket_type': ticket_type,
            }

            # Envoyer l'email au client (utilise helper existant qui ajoute le logo)
            try:
                envoyer_email_avec_logo(
                    request=request,
                    sujet=f"Votre ticket WiFi - {ticket_type.nom}",
                    template_html='emails/ticket_client.html',
                    template_txt='emails/ticket_client.txt',
                    context=context,
                    destinataire=data.get('email')
                )
            except Exception as e:
                # ne bloque pas la création du ticket mais log pour debug
                print(f"Erreur envoi email ticket: {e}")

            return render(request, 'core/tickets_confirmation.html', {
                'ticket': ticket,
                'nom': data.get('nom'),
                'email': data.get('email'),
                'ticket_type': ticket_type,
            })
    else:
        form = WifiTicketPurchaseForm()

    return render(request, 'core/tickets_acheter.html', {
        'ticket_type': ticket_type,
        'form': form,
    })
