from django.db import models, transaction
from django.db.models import F, Q
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .storage import DedupFileSystemStorage 

dedup_storage = DedupFileSystemStorage()


class Agence(models.Model):
    nom = models.CharField(max_length=200, blank=True, null=True)
    adresse = models.TextField(blank=True, null=True)
    telephone = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return self.nom or f"Agence #{self.pk}"

class MessageContact(models.Model):
    nom = models.CharField(max_length=100)
    email = models.EmailField()
    sujet = models.CharField(max_length=150)
    message = models.TextField()
    date_envoye = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nom} - {self.sujet}"

class ZoneCouverture(models.Model):
    region = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    def __str__(self):
        return self.region

class Commune(models.Model):
    nom = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    zone = models.ForeignKey(ZoneCouverture, related_name='communes', on_delete=models.CASCADE)

    def __str__(self):
        return self.nom
    
class Slider(models.Model):
    titre = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='quickblocks/', storage=dedup_storage)  # ← AJOUTÉ
    is_active = models.BooleanField(default=True)
    ordre = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.titre
    
class Actualite(models.Model):
    titre = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    date_pub = models.DateField(auto_now_add=True)
    lien = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.titre

class ActualiteImage(models.Model):
    actualite = models.ForeignKey(Actualite, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='blog/', storage=dedup_storage)  # ← AJOUTÉ
    alt = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.alt or f"Image de {self.actualite.titre}"

class Logo(models.Model):
    image = models.ImageField(upload_to='logos/', storage=dedup_storage)  # ← AJOUTÉ
    alt = models.CharField(max_length=100, blank=True)
    actif = models.BooleanField(default=True)
    
    def save(self, *args, **kwargs):
        if self.actif:
            Logo.objects.all().update(actif=False)
        super().save(*args, **kwargs)

class QuickBlock(models.Model):
    title = models.CharField(max_length=100)
    image = models.ImageField(upload_to='quickblocks/', storage=dedup_storage)  # ← AJOUTÉ
    url_name = models.CharField(max_length=50, help_text="Nom de l'URL Django (ex: 'forfaits', 'faq')")
    description = models.CharField(max_length=200, blank=True)
    extra_description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Classe Bootstrap Icons (ex: 'bi-box-seam')")
    ordre = models.PositiveIntegerField(default=0)

    def get_url(self):
        from django.urls import reverse
        return reverse(self.url_name)

    def __str__(self):
        return self.title
    
class FaqSection(models.Model):
    titre = models.CharField(max_length=150)
    ordre = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.titre

class Faq(models.Model):
    section = models.ForeignKey(FaqSection, related_name='faqs', on_delete=models.CASCADE)
    question = models.CharField(max_length=255)
    ordre = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.question

class FaqImage(models.Model):
    faq = models.ForeignKey(Faq, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='faq/', storage=dedup_storage)  # ← AJOUTÉ
    legend = models.CharField(max_length=255, blank=True)

class FaqStep(models.Model):
    faq = models.ForeignKey(Faq, related_name='steps', on_delete=models.CASCADE)
    texte = models.TextField()
    ordre = models.PositiveIntegerField(default=0)

class FaqStepImage(models.Model):
    step = models.ForeignKey(FaqStep, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='faq_steps/', storage=dedup_storage)  # ← AJOUTÉ
    legend = models.CharField(max_length=255, blank=True)

from django.db import models
from django.contrib.auth.models import User

class Forfait(models.Model):
    nom = models.CharField(max_length=255)
    description1 = models.CharField(max_length=255, blank=True)
    description2 = models.CharField(max_length=255, blank=True)
    description3 = models.CharField(max_length=255, blank=True)
    description4 = models.CharField(max_length=255, blank=True)
    prix = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="Prix (GNF)")
    icone = models.CharField(max_length=50, blank=True)
    image = models.ImageField(upload_to='forfaits/', blank=True, null=True, storage=dedup_storage)  # ← AJOUTÉ
    type = models.CharField(max_length=10, choices=[('FO', 'Fibre Optique'), ('FH', 'Faisceau Hertzien')], default='FO')
    is_bon_plan = models.BooleanField(default=False)
    FORFAIT_COLOR_CHOICES = [
        ('#2596be', 'Bleu Sky (#2596be)'),
        ('#cf0606', 'Rouge CF (#cf0606)'),
    ]
    bg_color = models.CharField(
        max_length=7,
        choices=FORFAIT_COLOR_CHOICES,
        blank=True,
        null=True,
        help_text="Couleur d'arrière-plan (sélection : --bleu-sky ou --rouge-cf)",
    )

    def __str__(self):
        return self.nom

    def prix_affiche(self):
        if self.prix is None:
            return "Prix sur demande"
        return f"À partir de {int(self.prix):,} GNF / mois".replace(',', ' ')


class ForfaitDescription(models.Model):
    forfait = models.ForeignKey(Forfait, related_name='descriptions', on_delete=models.CASCADE)
    texte = models.TextField(help_text='Texte de description (affiché dans la carte)')
    ordre = models.PositiveIntegerField(default=0, help_text='Ordre d\'affichage (plus petit = en haut)')

    class Meta:
        ordering = ['ordre']

    def __str__(self):
        return f"Description {self.ordre} pour {self.forfait.nom}"
    
class Categorie(models.Model):
    nom = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.nom

class SousCategorie(models.Model):
    nom = models.CharField(max_length=100)
    categorie = models.ForeignKey(Categorie, related_name='sous_categories', on_delete=models.CASCADE)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.nom} ({self.categorie.nom})"

class Produit(models.Model):
    nom = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    prix = models.DecimalField(max_digits=10, decimal_places=2)
    taux_tva = models.DecimalField(max_digits=5, decimal_places=2, default=18.00, verbose_name="Taux TVA (%)")
    icone = models.CharField(max_length=50, blank=True)
    image = models.ImageField(upload_to='produits/', blank=True, null=True, storage=dedup_storage)  # ← AJOUTÉ
    sous_categorie = models.ForeignKey(SousCategorie, related_name='produits', on_delete=models.SET_NULL, blank=True, null=True)
    is_bon_plan = models.BooleanField(default=False)
    quantite = models.PositiveIntegerField(default=0, verbose_name="Quantité en stock")
    caracteristiques = models.TextField(blank=True, help_text="Caractéristiques techniques ou points forts du produit")
    reference = models.CharField(max_length=100, blank=True, help_text="Référence ou SKU du produit")
    date_ajout = models.DateTimeField(auto_now_add=True)

    @property
    def prix_ttc(self):
        return self.prix * (1 + self.taux_tva / 100)

    @property
    def tva_montant(self):
        return self.prix * (self.taux_tva / 100)

    def __str__(self):
         return getattr(self, 'nom', getattr(self, 'name', f'Produit #{self.pk}'))


    
class Panier(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date_creation = models.DateTimeField(auto_now_add=True)

class PanierItem(models.Model):
    panier = models.ForeignKey(Panier, related_name='items', on_delete=models.CASCADE)
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE)
    quantite = models.PositiveIntegerField(default=1)

class DemandeSouscription(models.Model):
    STATUT_CHOICES = [
        ("EN_ATTENTE", "En attente"),
        ("RDV_CONFIRME", "Rendez‑vous confirmé"),
        ("ETUDE_SITE", "Étude de site"),
        ("SURVEY", "Survey / Relevé de site"),
        ("POSE_BOOM", "Pose du boom"),
        ("COTATION", "Cotation / Devis"),
        ("SIGNE", "Client signé"),
        ("INSTALLATION", "Installation"),
        ("ACTIVATION", "Activation"),
        ("FACTURATION", "Facturation"),
        ("ANNULE", "Annulé"),
    ]
    nom = models.CharField(max_length=255)
    telephone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    forfait = models.ForeignKey(Forfait, on_delete=models.CASCADE)
    zone = models.ForeignKey(ZoneCouverture, on_delete=models.CASCADE)
    commune = models.ForeignKey(Commune, on_delete=models.CASCADE)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default="EN_ATTENTE")
    commercial = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="demandes_souscription",
        help_text="Commercial en charge de la demande",
        limit_choices_to=Q(groups__name__icontains='commercial'),
    )
    note_interne = models.TextField(blank=True, help_text="Note interne pour le suivi")
    date = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nom} - {self.forfait} ({self.get_statut_display()})"

    def clean(self):
        super().clean()
        if self.commercial and not self.commercial.groups.filter(name__icontains="commercial").exists():
            raise ValidationError({"commercial": "Le commercial doit appartenir au groupe 'Commercial'."})


class Order(models.Model):
    STATUT_CHOICES = (
        ('en_attente', 'En attente'),
        ('preparation', 'En préparation'),
        ('recuperee', 'Récupérée'),
        ('livree', 'Livrée'),
        ('annulee', 'Annulée'),
    )

    reference = models.CharField(max_length=50, unique=True)
    client = models.ForeignKey('auth.User', on_delete=models.CASCADE, null=True, blank=True, related_name='commandes_client')
    commercial = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='commandes_assigned',
        help_text="Commercial en charge de cette commande",
        limit_choices_to=Q(groups__name__icontains='commercial'),
    )
    date_commande = models.DateTimeField(auto_now_add=True)
    nom = models.CharField(max_length=150, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    telephone = models.CharField(max_length=50, blank=True, null=True)
    mode_reception = models.CharField(max_length=20, blank=True, null=True)
    agence = models.ForeignKey('Agence', null=True, blank=True, on_delete=models.SET_NULL)
    adresse_livraison = models.TextField(null=True, blank=True)
    commune = models.ForeignKey('Commune', null=True, blank=True, on_delete=models.SET_NULL)
    montant_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')

    @property
    def montant_total_ttc(self):
        return sum(item.total_ligne for item in self.items.all())

    def clean(self):
        super().clean()
        if self.commercial and not self.commercial.groups.filter(name__icontains="commercial").exists():
            raise ValidationError({"commercial": "Le commercial doit appartenir au groupe 'Commercial'."})

    def save(self, *args, **kwargs):
        if not self.pk:
            super().save(*args, **kwargs)
            return

        self.montant_total = self.montant_total_ttc

        old_status = None
        if self.pk:
            old = Order.objects.filter(pk=self.pk).only('statut').first()
            if old:
                old_status = old.statut

        confirmed_states = ('recuperee', 'livree')
        if old_status not in confirmed_states and self.statut in confirmed_states:
            self.debit_stock()

        super().save(*args, **kwargs)

        if old_status in confirmed_states and self.statut == 'annulee':
            self.restore_stock()

    def debit_stock(self):
        with transaction.atomic():
            for item in self.items.select_for_update():
                if getattr(item, 'stock_debited', False):
                    continue
                
                produit = Produit.objects.select_related('sous_categorie__categorie').filter(pk=item.produit_id).first()
                if not produit:
                    raise ValueError(f"Produit introuvable")
                
                produit_nom = produit.nom
                type_produit = "produit"
                if produit.sous_categorie and produit.sous_categorie.categorie:
                    type_produit = produit.sous_categorie.categorie.nom.lower()
                
                updated = Produit.objects.filter(
                    pk=item.produit_id,
                    quantite__gte=item.quantite
                ).update(quantite=F('quantite') - item.quantite)
                
                if not updated:
                    message = (
                        f"Le stock pour l'{type_produit} \"{produit_nom}\" est insuffisant. "
                        f"Impossible de valider la commande.\n"
                        f"Veuillez remplir le stock ou réduire la quantité demandée."
                    )
                    raise ValueError(message)
                
                item.stock_debited = True
                item.save(update_fields=['stock_debited'])

    def restore_stock(self):
        with transaction.atomic():
            for item in self.items.select_for_update():
                if not getattr(item, 'stock_debited', False):
                    continue
                Produit.objects.filter(pk=item.produit_id).update(quantite=F('quantite') + item.quantite)
                item.stock_debited = False
                item.save(update_fields=['stock_debited'])

    class Meta:
        verbose_name = "Commande"
        verbose_name_plural = "Commandes"


class OrderItem(models.Model):
    commande = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    produit = models.ForeignKey('Produit', on_delete=models.CASCADE)
    quantite = models.PositiveIntegerField()
    prix_unitaire = models.DecimalField(max_digits=12, decimal_places=2)
    total_ligne = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    stock_debited = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.total_ligne = self.produit.prix_ttc * self.quantite
        super().save(*args, **kwargs)

    def __str__(self):
        produit_label = getattr(self.produit, 'nom', getattr(self.produit, 'name', f'Produit #{getattr(self.produit, "id", "?")}'))
        commande_ref = getattr(self.commande, 'reference', f'Commande #{getattr(self.commande, "id", "?")}')
        return f"{produit_label} ({self.quantite}) - {commande_ref}"


class WifiTicketType(models.Model):
    nom = models.CharField(max_length=100, help_text="Ex: 5 minutes, 30 minutes, 1 heure, 2 heures, 1 jour")
    duree_minutes = models.PositiveIntegerField(help_text="Durée en minutes")
    prix = models.DecimalField(max_digits=10, decimal_places=2, help_text="Prix en GNF")
    description = models.TextField(blank=True, help_text="Description optionnelle")
    is_active = models.BooleanField(default=True)
    ordre = models.PositiveIntegerField(default=0, help_text="Ordre d'affichage")

    class Meta:
        ordering = ['ordre', 'duree_minutes']
        verbose_name = "Type de ticket WiFi"
        verbose_name_plural = "Types de tickets WiFi"

    def __str__(self):
        return f"{self.nom} - {self.prix} GNF"


class WifiTicket(models.Model):
    ticket_type = models.ForeignKey(WifiTicketType, on_delete=models.CASCADE)
    identifiant = models.CharField(max_length=20, unique=True, help_text="Identifiant de connexion")
    mot_de_passe = models.CharField(max_length=20, help_text="Mot de passe de connexion")
    date_creation = models.DateTimeField(auto_now_add=True)
    date_premiere_connexion = models.DateTimeField(null=True, blank=True)
    date_expiration = models.DateTimeField(null=True, blank=True)
    is_used = models.BooleanField(default=False)
    date_utilisation = models.DateTimeField(null=True, blank=True)
    hotspot = models.CharField(max_length=100, blank=True, help_text="Nom du hotspot utilisé")

    class Meta:
        ordering = ['-date_creation']
        verbose_name = "Ticket WiFi"
        verbose_name_plural = "Tickets WiFi"

    def __str__(self):
        return f"{self.identifiant} - {self.ticket_type.nom}"

    def is_expired(self):
        if not self.date_expiration:
            return False
        return timezone.now() > self.date_expiration

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    @property
    def radcheck_expiration(self):
        return self.date_expiration + timezone.timedelta(minutes=5)