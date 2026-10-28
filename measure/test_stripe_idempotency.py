import decimal
from unittest import mock

from django.db import IntegrityError
from django.test import TestCase

from .models import Account, Ledger
from .tests import make_ghp_user
from .views import handle_checkout_session


class StripeSessionUniqueConstraintTests(TestCase):
    """The unique stripe_session_id constraint is the backstop when two deliveries race past the pre-check."""

    def setUp(self):
        self.user = make_ghp_user('payer@example.com')
        self.session = {
            'id': 'cs_test_race', 'client_reference_id': self.user.pk,
            'payment_intent': 'pi_test', 'amount_subtotal': 1234,
        }
        self.real_create = Ledger.objects.create

    def test_concurrent_duplicate_is_acknowledged_and_credited_once(self):
        def racing_create(**kwargs):
            # The other delivery inserts the row first; ours then hits the constraint
            self.real_create(**kwargs)
            raise IntegrityError('duplicate key value violates unique constraint')

        with mock.patch.object(Ledger.objects, 'create', side_effect=racing_create):
            response = handle_checkout_session(self.session)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Ledger.objects.filter(stripe_session_id='cs_test_race').count(), 1)
        self.assertEqual(Account.objects.get(ghp_user=self.user).balance, decimal.Decimal('12.34'))

    def test_other_integrity_error_is_not_acknowledged(self):
        # No row for this session exists, so the IntegrityError came from some other
        # constraint: the payment was not credited, so Stripe must keep retrying
        with mock.patch.object(Ledger.objects, 'create', side_effect=IntegrityError('some other constraint')):
            response = handle_checkout_session(self.session)

        self.assertNotEqual(response.status_code // 100, 2)
        self.assertFalse(Ledger.objects.filter(stripe_session_id='cs_test_race').exists())
        self.assertEqual(Account.objects.get(ghp_user=self.user).balance, decimal.Decimal('0.00'))
