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
