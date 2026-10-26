from django.contrib.auth.models import User
from django.test import TestCase, override_settings
import numpy as np
import decimal
import math
from django.urls import reverse
from django.utils import timezone
from .models import GHPUser, Account, Piece, Ledger, PieceReceipt
from .constants import GLAZE_TEMPS

# Create your tests here.


@override_settings(
    PRINT_SERVER_SECRET_KEY='chelsea-key',
    GREENWICH_PRINT_SERVER_SECRET_KEY='greenwich-key',
    BARROW_PRINT_SERVER_SECRET_KEY='barrow-key',
)
class PrintJobsV2LocationTests(TestCase):
    """get_print_jobs_optimized must only ever hand a print server its own location's receipts."""

    @classmethod
    def setUpTestData(cls):
        user = GHPUser.objects.create(
            username='potter@example.com', email='potter@example.com',
            first_name='Test', last_name='Potter',
        )
        # bulk_create skips Piece.save(), which does pricing/ledger work irrelevant here
        piece = Piece.objects.bulk_create([Piece(ghp_user=user, length=4, width=4, height=4)])[0]
        for location in ['Chelsea', 'Greenwich', 'Barrow']:
            PieceReceipt.objects.create(
                piece=piece, ghp_user_name='Test Potter', receipt_type='Bisque',
                length=4, width=4, height=4, piece_location=location,
            )

    def get_jobs(self, **params):
        return self.client.get(reverse('measure:get_print_jobs_optimized'), params, secure=True)

    def unprinted_locations(self):
        return set(PieceReceipt.objects.filter(printed=False).values_list('piece_location', flat=True))

    def test_matching_location_returns_only_that_location(self):
        response = self.get_jobs(secret_key='chelsea-key', location='Chelsea')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['location'], 'Chelsea')
        self.assertEqual(response.json()['count'], 1)
        self.assertEqual(self.unprinted_locations(), {'Greenwich', 'Barrow'})

    def test_omitted_location_returns_only_key_location(self):
        response = self.get_jobs(secret_key='barrow-key')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['location'], 'Barrow')
        self.assertEqual(response.json()['count'], 1)
        self.assertEqual(self.unprinted_locations(), {'Chelsea', 'Greenwich'})

    def slips(self, secret_key):
        return {job['id']: job['print_string'] for job in self.get_jobs(secret_key=secret_key).json()['unprinted_receipts']}

    def test_each_location_keeps_its_slip_wording(self):
        # Chelsea and Greenwich keep the /api/printjobs/ wording; Barrow keeps the v2 wording
        glaze = PieceReceipt.objects.create(
            piece=PieceReceipt.objects.first().piece, ghp_user_name='Test Potter', receipt_type='Glaze',
            length=4, width=4, height=4, piece_location='Greenwich',
        )
        greenwich = self.slips('greenwich-key')
        self.assertIn('SAVE THIS SLIP FOR', greenwich.pop(glaze.id))
        self.assertIn('YOUR PIECE & CLASS CHIP', greenwich.popitem()[1])
        self.assertIn('YOUR PIECE & CLASS CHIP', self.slips('chelsea-key').popitem()[1])
        barrow = self.slips('barrow-key').popitem()[1]
        self.assertIn('YOUR PIECE ON THE', barrow)
        self.assertNotIn('CLASS CHIP', barrow)

    def test_mismatched_location_is_rejected_and_prints_nothing(self):
        # e.g. a print server built with LOCATION = "Barrow" but given Chelsea's key
        response = self.get_jobs(secret_key='chelsea-key', location='Barrow')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.unprinted_locations(), {'Chelsea', 'Greenwich', 'Barrow'})

    def test_invalid_key_is_rejected(self):
        response = self.get_jobs(secret_key='wrong-key', location='Chelsea')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.unprinted_locations(), {'Chelsea', 'Greenwich', 'Barrow'})

    def test_non_ascii_key_is_rejected(self):
        response = self.get_jobs(secret_key='chelsea-kéy')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.unprinted_locations(), {'Chelsea', 'Greenwich', 'Barrow'})

    @override_settings(GREENWICH_PRINT_SERVER_SECRET_KEY='')
    def test_missing_key_does_not_match_unset_server_key(self):
        # An unset env var leaves that location's key as ''; a request with no key must not match it
        for params in [{}, {'secret_key': ''}, {'secret_key': '  '}]:
            response = self.get_jobs(**params)
            self.assertEqual(response.status_code, 403)
        self.assertEqual(self.unprinted_locations(), {'Chelsea', 'Greenwich', 'Barrow'})


def make_ghp_user(email):
    # GHPUser.save() creates the user's Account with a zero balance. Re-fetch so the
    # account is loaded from the database (Decimal balance), as it is in a real request.
    user = GHPUser.objects.create(username=email, email=email, first_name='Test', last_name='Potter')
    return GHPUser.objects.get(pk=user.pk)


class LedgerBalanceTests(TestCase):
    """Saving a new Ledger must apply its amount to the user's Account balance exactly once."""

    def test_new_ledgers_accumulate_into_balance(self):
        user = make_ghp_user('ledger@example.com')
        Ledger.objects.create(ghp_user=user, amount=decimal.Decimal('10.00'), transaction_type='manual_gh_add_misc_credit')
        Ledger.objects.create(ghp_user=user, amount=decimal.Decimal('-3.50'), transaction_type='manual_gh_add_misc_charge')
        self.assertEqual(Account.objects.get(ghp_user=user).balance, decimal.Decimal('6.50'))

    def test_resaving_existing_ledger_does_not_change_balance(self):
        user = make_ghp_user('resave@example.com')
        ledger = Ledger.objects.create(ghp_user=user, amount=decimal.Decimal('10.00'), transaction_type='manual_gh_add_misc_credit')
        ledger.note = 'edited'
        ledger.save()
        self.assertEqual(Account.objects.get(ghp_user=user).balance, decimal.Decimal('10.00'))


class AddCreditViewTests(TestCase):
    """add_credit_view must credit the user in the URL, whatever ghp_user the POST body names."""

    def setUp(self):
        self.target = make_ghp_user('target@example.com')
        self.other = make_ghp_user('other@example.com')
        staff = User.objects.create_superuser('staff', 'staff@example.com', 'pw')
        self.client.force_login(staff)

    def post_credit(self, amount, ghp_user):
        url = reverse('measure:add_credit', args=(self.target.pk,))
        return self.client.post(url, {
            'ghp_user': ghp_user.pk, 'amount': amount,
            'transaction_type': 'manual_gh_add_misc_credit', 'note': 'test',
        }, secure=True)

    def test_credit_goes_to_url_user_not_posted_user(self):
        response = self.post_credit('5.00', ghp_user=self.other)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Account.objects.get(ghp_user=self.target).balance, decimal.Decimal('5.00'))
        self.assertEqual(Account.objects.get(ghp_user=self.other).balance, decimal.Decimal('0.00'))

    def test_empty_amount_shows_form_error_instead_of_crashing(self):
        response = self.post_credit('', ghp_user=self.target)
        self.assertEqual(response.status_code, 200)
        self.assertIn('amount', response.context['form'].errors)
