from django import template
from django.conf import settings

register = template.Library()

@register.filter(is_safe=True)
def hide_price(value):
    """Masque les prix produits si le réglage HIDE_PRODUCT_PRICES est True.

    Ne doit être utilisé que pour les prix de produits, pas pour des forfaits ou
    tickets. La valeur renvoyée est soit la valeur passée (pour affichage), soit
    une chaîne vide.
    """
    if getattr(settings, 'HIDE_PRODUCT_PRICES', False):
        return ''
    return value
