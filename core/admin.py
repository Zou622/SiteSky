from django.contrib import admin, messages
from django.urls import path, reverse
from django.shortcuts import get_object_or_404, redirect
from django.utils.html import format_html

from .models import DemandeSouscription

# Admin CRM pour DemandeSouscription
@admin.register(DemandeSouscription)
class DemandeSouscriptionAdmin(admin.ModelAdmin):
    def commercial_display(self, obj):
        if obj.commercial:
            full_name = obj.commercial.get_full_name()
            return f"{full_name} ({obj.commercial.username})" if full_name else obj.commercial.username
        return "-"
    commercial_display.short_description = "Pris en charge par"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Personnaliser les FK pour éviter des liens 403 et rendre certains champs en lecture seule.

        Les commerciaux ne doivent pas pouvoir cliquer sur les liens de consultation/modification
        pour les objets liés (zone, commune, forfait), même si Django leur donne ce droit.
        """
        # Limiter le choix du commercial au groupe "Commercial".
        if db_field.name == 'commercial':
            from django.contrib.auth import get_user_model
            User = get_user_model()
            kwargs['queryset'] = User.objects.filter(groups__name__icontains='commercial')

        field = super().formfield_for_foreignkey(db_field, request, **kwargs)

        # Pour certains champs liés (zone, commune, forfait), les commerciaux ne doivent
        # pas pouvoir cliquer sur les liens de consultation/modification (pas de 403).
        if db_field.name in ('zone', 'commune', 'forfait') and request.user.groups.filter(name='Commercial').exists():
            widget = getattr(field, 'widget', None)
            if widget is not None:
                for attr in ('can_view_related', 'can_change_related', 'can_add_related'):
                    if hasattr(widget, attr):
                        setattr(widget, attr, False)

        return field

    list_display = ("nom", "forfait", "zone", "commune", "statut", "commercial_display", "date", "date_modification")
    # colonne action par ligne
    def action_prendre(self, obj):
        if obj.statut == "EN_ATTENTE" and not obj.commercial:
            url = reverse('admin:core_demandesouscription_prendre_en_charge', args=[obj.pk])
            return format_html('<a class="button" href="{}">Prendre en charge</a>', url)
        return '-'
    action_prendre.short_description = 'Prendre en charge'
    # insérer action_prendre avant la date
    list_display = ("nom", "forfait", "zone", "commune", "statut", "commercial_display", "action_prendre", "date", "date_modification")
    list_filter = ("statut", "commercial", "zone", "commune", "forfait")
    search_fields = ("nom", "email", "telephone", "note_interne")
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        return form

    def forfait_display(self, obj):
        return obj.forfait if obj.forfait else '-'
    forfait_display.short_description = 'Forfait'

    def zone_display(self, obj):
        return obj.zone if obj.zone else '-'
    zone_display.short_description = 'Zone'

    def commune_display(self, obj):
        return obj.commune if obj.commune else '-'
    commune_display.short_description = 'Commune'

    def get_readonly_fields(self, request, obj=None):
        # Par défaut (admin complet), seuls le date et la date de modif sont readonly.
        if request.user.is_superuser or (request.user.is_staff and not request.user.groups.filter(name="Commercial").exists()):
            return ("date", "date_modification")

        # Pour les commerciaux, on affiche en readonly les champs liés (pas de liens cliquables)
        readonly = [
            "nom", "telephone", "email",
            "forfait_display", "zone_display", "commune_display",
            "statut", "commercial_display", "note_interne",
            "date", "date_modification",
        ]

        # Le commercial assigné peut modifier le statut et la note interne s'il est déjà assigné
        if obj and obj.commercial == request.user:
            if "statut" in readonly:
                readonly.remove("statut")
            if "note_interne" in readonly:
                readonly.remove("note_interne")

        return readonly

    def save_model(self, request, obj, form, change):
        # Si le commercial clique sur le bouton 'Prendre en charge', on l'assigne.
        # Le statut reste "EN_ATTENTE" tant qu'il n'a pas contacté le client.
        if request.user.groups.filter(name="Commercial").exists() and request.POST.get('take_charge') == '1':
            if not obj.commercial:
                obj.commercial = request.user
        super().save_model(request, obj, form, change)
    # Fieldsets dynamiques : les commerciaux (sans droits sur Zone/Commune/Forfait) voient une version en lecture seule
    # (via les méthodes forfait_display/zone_display/commune_display) pour éviter les liens 403.
    default_fieldsets = (
        (None, {
            "fields": ("nom", "telephone", "email", "forfait", "zone", "commune", "statut", "commercial", "note_interne", "date", "date_modification")
        }),
    )

    readonly_fieldsets_for_commercial = (
        (None, {
            "fields": ("nom", "telephone", "email", "forfait_display", "zone_display", "commune_display", "statut", "commercial_display", "note_interne", "date", "date_modification")
        }),
    )

    def get_fieldsets(self, request, obj=None):
        if request.user.groups.filter(name="Commercial").exists() and not (request.user.is_superuser or (request.user.is_staff and not request.user.groups.filter(name="Commercial").exists())):
            return self.readonly_fieldsets_for_commercial
        return self.default_fieldsets

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        """Ajouter le flag is_commercial au contexte pour le template."""
        extra_context = extra_context or {}
        extra_context['is_commercial'] = request.user.groups.filter(name="Commercial").exists() and not request.user.is_superuser
        return super().changeform_view(request, object_id, form_url, extra_context)

    actions = ["prendre_en_charge", "marquer_signe", "marquer_annule"]

    @admin.action(description="Prendre en charge (assigner à moi)")
    def prendre_en_charge(self, request, queryset):
        count = 0
        for demande in queryset:
            if not demande.commercial and demande.statut == "EN_ATTENTE":
                demande.commercial = request.user
                demande.save(update_fields=["commercial"])
                count += 1
        self.message_user(request, f"{count} demandes prises en charge par vous.")

    # Vue admin pour prise en charge par-ligne
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('<int:pk>/prendre-en-charge/', self.admin_site.admin_view(self.prendre_en_charge_view), name='core_demandesouscription_prendre_en_charge'),
        ]
        return custom + urls

    def prendre_en_charge_view(self, request, pk, *args, **kwargs):
        # accès réservé aux superusers et au groupe Commercial
        if not (request.user.is_superuser or request.user.groups.filter(name='Commercial').exists()):
            self.message_user(request, "Accès refusé.", level=messages.ERROR)
            return redirect(reverse('admin:core_demandesouscription_changelist'))
        demande = get_object_or_404(DemandeSouscription, pk=pk)
        if demande.commercial or demande.statut != 'EN_ATTENTE':
            self.message_user(request, "La demande ne peut pas être prise en charge.", level=messages.WARNING)
            return redirect(reverse('admin:core_demandesouscription_changelist'))
        demande.commercial = request.user
        demande.save(update_fields=['commercial'])
        name = request.user.get_full_name() or request.user.username
        self.message_user(request, f"Demande '{demande.nom}' prise en charge par {name}.")
        return redirect(reverse('admin:core_demandesouscription_changelist'))

    @admin.action(description="Marquer comme signé")
    def marquer_signe(self, request, queryset):
        updated = queryset.update(statut="SIGNE")
        self.message_user(request, f"{updated} demandes marquées comme signées.")

    @admin.action(description="Marquer comme annulé")
    def marquer_annule(self, request, queryset):
        updated = queryset.update(statut="ANNULE")
        self.message_user(request, f"{updated} demandes annulées.")
from django.contrib import admin, messages
# Register your models here.
from .models import MessageContact, Slider, Actualite, Logo, ActualiteImage, QuickBlock, Faq, FaqStep, FaqStepImage, FaqSection, Forfait, Produit, ZoneCouverture, Commune, Categorie, SousCategorie, Agence, Order, OrderItem, WifiTicketType, WifiTicket

from django import forms
from django.core.exceptions import ValidationError
import re

from django.contrib import admin
from .models import Order, OrderItem
from .views import envoyer_email_avec_logo  # Ajout de l'import


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    readonly_fields = ['produit', 'prix_unitaire', 'quantite', 'total_ligne']
    extra = 0

from .models import Order

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    def commercial_display(self, obj):
        if obj.commercial:
            full_name = obj.commercial.get_full_name()
            return f"{full_name} ({obj.commercial.username})" if full_name else obj.commercial.username
        return "-"
    commercial_display.short_description = "Chargé par"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Limiter le choix du commercial au groupe "Commercial"."""
        if db_field.name == 'commercial':
            from django.contrib.auth import get_user_model
            User = get_user_model()
            kwargs['queryset'] = User.objects.filter(groups__name__icontains='commercial')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def action_prendre(self, obj):
        """Action en ligne pour prendre en charge une commande"""
        if obj.statut == "en_attente" and not obj.commercial:
            url = reverse('admin:core_order_prendre_en_charge', args=[obj.pk])
            return format_html('<a class="button" href="{}">Prendre en charge</a>', url)
        return '-'
    action_prendre.short_description = 'Prendre en charge'
    
    list_display = ['reference', 'nom', 'montant_total', 'statut', 'commercial_display', 'action_prendre', 'mode_reception', 'date_commande']
    list_filter = ['statut', 'commercial', 'mode_reception', 'date_commande']
    search_fields = ['reference', 'nom', 'email', 'telephone']
    inlines = [OrderItemInline]
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Adapter les choix de statut en fonction du mode de réception
        if obj and 'statut' in form.base_fields:
            if obj.mode_reception == 'agence':
                # Pour retrait en agence: en_attente, preparation, recuperée, annulée
                form.base_fields['statut'].choices = [
                    ('en_attente', 'En attente'),
                    ('preparation', 'En préparation'),
                    ('recuperee', 'Récupérée'),
                    ('annulee', 'Annulée'),
                ]
            elif obj.mode_reception == 'livraison':
                # Pour livraison: en_attente, preparation, livrée, annulée
                form.base_fields['statut'].choices = [
                    ('en_attente', 'En attente'),
                    ('preparation', 'En préparation'),
                    ('livree', 'Livrée'),
                    ('annulee', 'Annulée'),
                ]
        return form

    def client_display(self, obj):
        return obj.client if obj.client else '-'
    client_display.short_description = 'Client'

    def agence_display(self, obj):
        return obj.agence if obj.agence else '-'
    agence_display.short_description = 'Agence'

    def commune_display(self, obj):
        return obj.commune if obj.commune else '-'
    commune_display.short_description = 'Commune'

    def get_readonly_fields(self, request, obj=None):
        # Superuser peut modifier tout sauf reference et date
        if request.user.is_superuser:
            return ['reference', 'date_commande']
        # Staff non commercial peut modifier tout sauf reference et date
        if request.user.is_staff and not request.user.groups.filter(name="Commercial").exists():
            return ['reference', 'date_commande']
        # Commercial : champs liés en lecture seule (plus de lien cliquable)
        if request.user.groups.filter(name="Commercial").exists():
            readonly = ['reference', 'client_display', 'date_commande', 'commercial_display', 'nom', 'email', 'telephone',
                        'montant_total', 'mode_reception', 'agence_display', 'adresse_livraison', 'commune_display']
            # Commercial assigné peut modifier le statut
            if obj and obj.commercial == request.user:
                # on garde statut editable
                pass
            else:
                readonly.append('statut')
            return readonly
        # Par défaut
        return ['reference', 'date_commande', 'commercial']

    def save_model(self, request, obj, form, change):
        # Assigne automatiquement le commercial lors de la première modification
        if not obj.commercial and request.user.groups.filter(name="Commercial").exists():
            obj.commercial = request.user
        try:
            super().save_model(request, obj, form, change)
        except ValueError as e:
            # Capturer les erreurs de stock insuffisant et les afficher comme message d'erreur
            error_msg = str(e)
            self.message_user(request, error_msg, level=messages.ERROR)

    default_fieldsets = (
        ("Informations client", {
            "fields": ("reference", "client", "nom", "email", "telephone", "date_commande")
        }),
        ("Commande", {
            "fields": ("statut", "commercial", "montant_total", "mode_reception", "agence", "adresse_livraison", "commune")
        }),
    )

    readonly_fieldsets_for_commercial = (
        ("Informations client", {
            "fields": ("reference", "client_display", "nom", "email", "telephone", "date_commande")
        }),
        ("Commande", {
            "fields": ("statut", "commercial_display", "montant_total", "mode_reception", "agence_display", "adresse_livraison", "commune_display")
        }),
    )

    def get_fieldsets(self, request, obj=None):
        if request.user.groups.filter(name="Commercial").exists() and not request.user.is_superuser:
            return self.readonly_fieldsets_for_commercial
        return self.default_fieldsets

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        extra_context = extra_context or {}
        from django.conf import settings
        extra_context['is_commercial'] = request.user.groups.filter(name="Commercial").exists()
        extra_context['hide_product_prices'] = settings.HIDE_PRODUCT_PRICES
        return super().changeform_view(request, object_id, form_url, extra_context)

    actions = ["prendre_en_charge", "marquer_confirme", "marquer_preparation", "marquer_annule"]

    @admin.action(description="Prendre en charge (assigner à moi)")
    def prendre_en_charge(self, request, queryset):
        count = 0
        for cmd in queryset:
            if not cmd.commercial and cmd.statut == "en_attente":
                cmd.commercial = request.user
                cmd.save(update_fields=["commercial"])
                count += 1
        self.message_user(request, f"{count} commandes prises en charge par vous.")

    # Vue admin pour prise en charge par ligne
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('<int:pk>/prendre-en-charge/', self.admin_site.admin_view(self.prendre_en_charge_view), name='core_order_prendre_en_charge'),
        ]
        return custom + urls

    def prendre_en_charge_view(self, request, pk, *args, **kwargs):
        # accès réservé aux superusers et au groupe Commercial
        if not (request.user.is_superuser or request.user.groups.filter(name='Commercial').exists()):
            self.message_user(request, "Accès refusé.", level=messages.ERROR)
            return redirect(reverse('admin:core_order_changelist'))
        commande = get_object_or_404(Order, pk=pk)
        if commande.commercial or commande.statut != 'en_attente':
            self.message_user(request, "La commande ne peut pas être prise en charge.", level=messages.WARNING)
            return redirect(reverse('admin:core_order_changelist'))
        commande.commercial = request.user
        commande.save(update_fields=['commercial'])
        name = request.user.get_full_name() or request.user.username
        self.message_user(request, f"Commande '{commande.reference}' prise en charge par {name}.")
        return redirect(reverse('admin:core_order_changelist'))

    @admin.action(description="Marquer comme récupérée")
    def marquer_confirme(self, request, queryset):
        updated = queryset.filter(mode_reception='agence').update(statut="recuperee")
        self.message_user(request, f"{updated} commandes marquées comme récupérées.")

    @admin.action(description="Marquer comme livrée")
    def marquer_preparation(self, request, queryset):
        updated = queryset.filter(mode_reception='livraison').update(statut="livree")
        self.message_user(request, f"{updated} commandes marquées comme livrées.")

    @admin.action(description="Marquer comme annulée")
    def marquer_annule(self, request, queryset):
        updated = queryset.update(statut="annulee")
        self.message_user(request, f"{updated} commandes annulées.")

@admin.action(description="Confirmer les commandes sélectionnées")
def action_confirm_orders(modeladmin, request, queryset):
    for order in queryset:
        try:
            old_status = order.statut
            order.statut = 'confirme'
            order.save()
            messages.success(request, f"Commande {order.reference} confirmée.")
        except ValueError as e:
            order.statut = old_status
            order.save(update_fields=['statut'])
            messages.error(request, f"Erreur confirmation {order.reference} : {e}")
            # Restauration de l'ancien statut
@admin.action(description="Annuler les commandes sélectionnées (restaure le stock si nécessaire)")
def action_cancel_orders(modeladmin, request, queryset):
    for order in queryset:
        order.statut = 'annule'
        try:
            order.save()
            messages.success(request, f"Commande {order.reference} annulée.")
        except Exception as e:
            messages.error(request, f"Erreur annulation {order.reference} : {e}")


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
        # on attend 9 chiffres (sans +224), et préfixes valides en Guinée (61,62,65,66)
        if not re.match(r'^(61|62|65|66)[0-9]{7}$', tel):
            raise ValidationError("Veuillez saisir un numéro valide")
        return tel

class ActualiteImageInline(admin.TabularInline):
    model = ActualiteImage
    extra = 3  # nombre de formulaires vides affichés par défaut
    fields = ['image', 'alt']
    # Tu peux aussi ajouter 'image' dans readonly_fields si besoin

@admin.register(Actualite)
class ActualiteAdmin(admin.ModelAdmin):
    inlines = [ActualiteImageInline]
    list_display = ('titre', 'date_pub')
    search_fields = ('titre',)


class FaqStepImageInline(admin.TabularInline):
    model = FaqStepImage
    extra = 1

class FaqStepInline(admin.StackedInline):
    model = FaqStep
    extra = 1

class FaqInline(admin.StackedInline):
    model = Faq
    extra = 1

@admin.register(FaqSection)
class FaqSectionAdmin(admin.ModelAdmin):
    inlines = [FaqInline]

@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ('nom', 'sous_categorie', 'prix', 'quantite')
    list_filter = ('sous_categorie',)
    search_fields = ('nom',)

# Admin simple pour SousCategorie
@admin.register(SousCategorie)
class SousCategorieAdmin(admin.ModelAdmin):
    list_display = ('nom', 'categorie')
    list_filter = ('categorie',)
    search_fields = ('nom',)


# Admin simple pour Categorie
@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display = ('nom',)
    search_fields = ('nom',)

# Inline to manage communes directly when editing a zone
class CommuneInline(admin.TabularInline):
    model = Commune
    extra = 1

@admin.register(ZoneCouverture)
class ZoneCouvertureAdmin(admin.ModelAdmin):
    list_display = ('region',)
    search_fields = ('region',)
    inlines = [CommuneInline]

# Register Commune separately too in case you need to manage them standalone
@admin.register(Commune)
class CommuneAdmin(admin.ModelAdmin):
    list_display = ('nom', 'zone')
    list_filter = ('zone',)
    search_fields = ('nom',)

admin.site.register(MessageContact)
admin.site.register(Slider)
admin.site.register(Logo)
admin.site.register(QuickBlock)





from django.contrib import admin
from .models import ForfaitDescription


class ForfaitDescriptionInline(admin.TabularInline):
    model = ForfaitDescription
    extra = 3
    fields = ('ordre', 'texte')


# re-register ForfaitAdmin to include inline (ignore if not previously registered)
from django.contrib.admin.sites import NotRegistered
try:
    admin.site.unregister(Forfait)
except NotRegistered:
    pass


@admin.register(Forfait)
class ForfaitAdmin(admin.ModelAdmin):
    inlines = [ForfaitDescriptionInline]
    list_display = ('nom', 'prix', 'type', 'is_bon_plan', 'bg_color')
    list_filter = ('type', 'is_bon_plan')
    search_fields = ('nom',)
    fieldsets = (
        ('Informations Générales', {
            'fields': ('nom', 'image', 'icone')
        }),
        ('Affichage', {
            'fields': ('is_bon_plan', 'bg_color')
        }),
        ('Configuration', {
            'fields': ('type', 'prix')
        }),
    )

admin.site.register(Agence)


# Admin pour les tickets WiFi
@admin.register(WifiTicketType)
class WifiTicketTypeAdmin(admin.ModelAdmin):
    list_display = ('nom', 'duree_minutes', 'prix', 'is_active')
    list_filter = ('is_active', 'duree_minutes')
    search_fields = ('nom',)
    list_editable = ('is_active',)
    
    fieldsets = (
        ('Informations Générales', {
            'fields': ('nom', 'description')
        }),
        ('Configuration', {
            'fields': ('duree_minutes', 'prix', 'is_active')
        }),
    )


@admin.register(WifiTicket)
class WifiTicketAdmin(admin.ModelAdmin):
    list_display = ('identifiant', 'ticket_type', 'date_creation', 'date_expiration', 'is_expired')
    list_filter = ('ticket_type', 'date_creation', 'date_expiration')
    search_fields = ('identifiant', 'mot_de_passe')
    readonly_fields = ('identifiant', 'mot_de_passe', 'date_creation', 'date_expiration', 'is_expired')
    
    fieldsets = (
        ('Identifiants', {
            'fields': ('identifiant', 'mot_de_passe'),
            'description': 'Les identifiants sont générés automatiquement'
        }),
        ('Configuration', {
            'fields': ('ticket_type',)
        }),
        ('Dates', {
            'fields': ('date_creation', 'date_expiration'),
            'classes': ('collapse',)
        }),
    )
    
    def is_expired(self, obj):
        return obj.is_expired()
    is_expired.short_description = "Expiré ?"
    is_expired.boolean = True
