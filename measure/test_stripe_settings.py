import decimal
import hashlib
import hmac
import importlib.util
import json
import os
import time
from pathlib import Path
from unittest import mock

from django.core.files.storage import FileSystemStorage
from django.core.files.storage.handler import StorageHandler
from django.test import TestCase, SimpleTestCase, override_settings

from .models import Ledger
from .tests import make_ghp_user

SETTINGS_PATH = Path(__file__).resolve().parent.parent / 'ebdjango' / 'settings.py'
WEBHOOK_SECRET = 'whsec_test_secret'


def sign_payload(payload, secret):
    # Same scheme Stripe uses for the Stripe-Signature header: HMAC-SHA256 of "<t>.<payload>"
    timestamp = int(time.time())
    signature = hmac.new(secret.encode('utf-8'), f'{timestamp}.{payload}'.encode('utf-8'), hashlib.sha256).hexdigest()
    return f't={timestamp},v1={signature}'


def checkout_event(ghp_user, session_id='cs_test_1', amount_subtotal=1234,
                   payment_status='paid', event_type='checkout.session.completed'):
    return json.dumps({
        'id': 'evt_' + session_id,
        'object': 'event',
        'type': event_type,
        'data': {'object': {
            'id': session_id,
            'object': 'checkout.session',
            'client_reference_id': str(ghp_user.pk),
            'amount_subtotal': amount_subtotal,
            'payment_status': payment_status,
            'payment_intent': 'pi_test',
            'customer_details': {'email': ghp_user.email},
        }},
    })


@override_settings(STRIPE_ENDPOINT_SECRET=WEBHOOK_SECRET)
class StripeWebhookTests(TestCase):
    """stripe_webhook must only credit accounts for authentic, actually-paid checkout sessions."""

    def setUp(self):
        self.user = make_ghp_user('buyer@example.com')

    def post_event(self, payload, secret=WEBHOOK_SECRET, signed=True):
        headers = {'HTTP_STRIPE_SIGNATURE': sign_payload(payload, secret)} if signed else {}
        return self.client.post('/webhook/', data=payload, content_type='application/json', secure=True, **headers)

    def test_paid_session_credits_account_once(self):
        response = self.post_event(checkout_event(self.user))
        self.assertEqual(response.status_code, 200)
        ledger = Ledger.objects.get(stripe_session_id='cs_test_1')
        self.assertEqual(ledger.ghp_user, self.user)
        self.assertEqual(ledger.amount, decimal.Decimal('12.34'))

    @override_settings(STRIPE_ENDPOINT_SECRET='')
    def test_empty_endpoint_secret_rejects_event_signed_with_empty_key(self):
        # With no secret configured, anyone can compute a "valid" HMAC using the empty key
        response = self.post_event(checkout_event(self.user), secret='')
        self.assertEqual(response.status_code, 500)
        self.assertFalse(Ledger.objects.filter(stripe_session_id='cs_test_1').exists())

    def test_missing_signature_header_returns_400(self):
        response = self.post_event(checkout_event(self.user), signed=False)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Ledger.objects.exists())

    def test_wrong_signature_returns_400(self):
        response = self.post_event(checkout_event(self.user), secret='whsec_attacker_guess')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Ledger.objects.exists())

    def test_unpaid_completed_session_is_not_credited(self):
        # Delayed payment methods complete the checkout with payment_status='unpaid'
        response = self.post_event(checkout_event(self.user, payment_status='unpaid'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Ledger.objects.exists())

    def test_async_payment_succeeded_credits_after_unpaid_completion(self):
        self.post_event(checkout_event(self.user, payment_status='unpaid'))
        self.assertFalse(Ledger.objects.exists())
        response = self.post_event(checkout_event(self.user, event_type='checkout.session.async_payment_succeeded'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Ledger.objects.filter(stripe_session_id='cs_test_1').count(), 1)

    def test_ledger_note_has_exact_cents(self):
        self.post_event(checkout_event(self.user, session_id='cs_cents', amount_subtotal=1234))
        self.post_event(checkout_event(self.user, session_id='cs_whole', amount_subtotal=1200))
        self.assertEqual(Ledger.objects.get(stripe_session_id='cs_cents').note, 'Stripe Payment of $12.34')
        self.assertEqual(Ledger.objects.get(stripe_session_id='cs_whole').note, 'Stripe Payment of $12.00')


HEROKU_ENV = {
    'DYNO': 'web.1',
    'DATABASE_URL': 'postgres://ghp:pw@db.example.com:5432/ghp',
    'GHP_DJANGO_SK': 'test-secret-key',
}


def load_settings(env):
    """Execute ebdjango/settings.py afresh under exactly `env`, returning the module."""
    spec = importlib.util.spec_from_file_location('settings_under_test', SETTINGS_PATH)
    module = importlib.util.module_from_spec(spec)
    with mock.patch.dict(os.environ, env, clear=True):
        spec.loader.exec_module(module)
    return module


class HerokuSettingsTests(SimpleTestCase):
    """Settings as computed on a Heroku web dyno (DYNO set, CI unset)."""

    def test_project_logging_config_survives_django_on_heroku(self):
        loggers = load_settings(HEROKU_ENV).LOGGING['loggers']
        self.assertIn('django.request', loggers)
        self.assertIn('measure', loggers)
        self.assertEqual(loggers['measure']['level'], 'INFO')

    def test_database_keeps_statement_timeout_and_ssl(self):
        db = load_settings(HEROKU_ENV).DATABASES['default']
        self.assertEqual(db['NAME'], 'ghp')
        self.assertEqual(db['HOST'], 'db.example.com')
        self.assertEqual(db['OPTIONS'], {'sslmode': 'require', 'options': '-c statement_timeout=25000'})
        self.assertEqual(db['CONN_MAX_AGE'], 600)
        self.assertTrue(db['CONN_HEALTH_CHECKS'])

    def test_default_file_storage_is_configured(self):
        storages = load_settings(HEROKU_ENV).STORAGES
        self.assertIsInstance(StorageHandler(storages)['default'], FileSystemStorage)
        self.assertEqual(storages['staticfiles']['BACKEND'], 'whitenoise.storage.CompressedManifestStaticFilesStorage')

    def test_publishable_key_has_no_test_mode_fallback(self):
        self.assertEqual(load_settings(HEROKU_ENV).STRIPE_PUBLISHABLE_KEY, '')
        env = dict(HEROKU_ENV, STRIPE_PUBLISHABLE_KEY='pk_live_example')
        self.assertEqual(load_settings(env).STRIPE_PUBLISHABLE_KEY, 'pk_live_example')

    def test_unchanged_django_on_heroku_settings(self):
        s = load_settings(HEROKU_ENV)
        self.assertEqual(s.ALLOWED_HOSTS, ['*'])
        self.assertEqual(s.SECRET_KEY, 'test-secret-key')
        self.assertEqual(s.STATIC_URL, '/static/')
        self.assertEqual(s.STATIC_ROOT, os.path.join(s.BASE_DIR, 'staticfiles'))
        self.assertEqual(load_settings(dict(HEROKU_ENV, SECRET_KEY='override')).SECRET_KEY, 'override')

    def test_heroku_ci_still_uses_database_url_as_test_database(self):
        db = load_settings(dict(HEROKU_ENV, CI='true')).DATABASES['default']
        self.assertEqual(db['NAME'], 'ghp')
        self.assertEqual(db['TEST']['NAME'], 'ghp')


class EmailBackendSettingsTests(SimpleTestCase):
    """Without Mailgun, password reset emails (which contain reset tokens) must not be printed to logs in production."""

    CONSOLE = 'django.core.mail.backends.console.EmailBackend'
    SMTP = 'django.core.mail.backends.smtp.EmailBackend'

    def test_production_without_mailgun_does_not_use_console_backend(self):
        self.assertEqual(load_settings(HEROKU_ENV).EMAIL_BACKEND, self.SMTP)

    def test_debug_without_mailgun_uses_console_backend(self):
        self.assertEqual(load_settings(dict(HEROKU_ENV, DJANGO_DEBUG='1')).EMAIL_BACKEND, self.CONSOLE)

    def test_mailgun_and_explicit_backend(self):
        self.assertEqual(load_settings(dict(HEROKU_ENV, MAILGUN_SMTP_PASSWORD='x')).EMAIL_BACKEND, self.SMTP)
        self.assertEqual(load_settings(dict(HEROKU_ENV, EMAIL_BACKEND=self.CONSOLE)).EMAIL_BACKEND, self.CONSOLE)
