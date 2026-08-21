from django.test import SimpleTestCase, override_settings
from django.urls import reverse


@override_settings(SECURE_SSL_REDIRECT=False)
class PublicSecurityTests(SimpleTestCase):
    def test_healthcheck_is_available_without_database_access(self):
        response = self.client.get(reverse('healthz'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'ok')

    def test_cart_addition_rejects_get_requests(self):
        response = self.client.get(reverse('ajouter_au_panier', args=[1]))

        self.assertEqual(response.status_code, 405)
