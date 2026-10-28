from django.test import TestCase, override_settings
from django.urls import reverse
from .models import Piece, PieceReceipt
from .tests import make_ghp_user


@override_settings(
    PRINT_SERVER_SECRET_KEY='chelsea-key',
    GREENWICH_PRINT_SERVER_SECRET_KEY='greenwich-key',
    BARROW_PRINT_SERVER_SECRET_KEY='barrow-key',
)
class PrintJobsTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        user = make_ghp_user('potter@example.com')
        # bulk_create skips Piece.save(), which does pricing/ledger work irrelevant here
        piece = Piece.objects.bulk_create([Piece(ghp_user=user, length=4, width=4, height=4)])[0]
        cls.receipts = {
            location: PieceReceipt.objects.create(
                piece=piece, ghp_user_name='Test Potter', receipt_type='Bisque',
                length=4, width=4, height=4, piece_location=location,
            )
            for location in ['Chelsea', 'Greenwich', 'Barrow']
        }

    def unprinted_locations(self):
        return set(PieceReceipt.objects.filter(printed=False).values_list('piece_location', flat=True))


class OldPrintJobsPostTests(PrintJobsTestCase):
    """POST /api/printjobs/ must never accept a missing key, even when a location's key setting is unset."""

    def mark_printed(self, **data):
        return self.client.post(reverse('measure:get_print_jobs_chelsea'), data, secure=True)

    @override_settings(PRINT_SERVER_SECRET_KEY='')
    def test_missing_key_does_not_match_unset_server_key(self):
        chelsea_id = str(self.receipts['Chelsea'].id)
        for data in [{}, {'secret_key': ''}, {'secret_key': '  '}]:
            response = self.mark_printed(receipt_ids=chelsea_id, **data)
            self.assertEqual(response.status_code, 403)
        self.assertEqual(self.unprinted_locations(), {'Chelsea', 'Greenwich', 'Barrow'})

    def test_invalid_key_is_rejected(self):
        response = self.mark_printed(secret_key='wrong-key', receipt_ids=str(self.receipts['Chelsea'].id))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.unprinted_locations(), {'Chelsea', 'Greenwich', 'Barrow'})

    def test_non_ascii_key_is_rejected(self):
        response = self.mark_printed(secret_key='chelsea-kéy', receipt_ids=str(self.receipts['Chelsea'].id))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.unprinted_locations(), {'Chelsea', 'Greenwich', 'Barrow'})

    def test_valid_key_marks_only_its_location(self):
        ids = ','.join(str(receipt.id) for receipt in self.receipts.values())
        response = self.mark_printed(secret_key='greenwich-key', receipt_ids=ids)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.unprinted_locations(), {'Chelsea', 'Barrow'})


class PrintJobsV2KeyHeaderTests(PrintJobsTestCase):
    """The v2 endpoint takes the key from the X-Print-Server-Key header, and still from ?secret_key=."""

    def get_jobs(self, headers=None, **params):
        return self.client.get(reverse('measure:get_print_jobs_optimized'), params, headers=headers, secure=True)

    def test_key_in_header(self):
        response = self.get_jobs(headers={'X-Print-Server-Key': 'chelsea-key'}, location='Chelsea')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['location'], 'Chelsea')
        self.assertEqual(self.unprinted_locations(), {'Greenwich', 'Barrow'})

    def test_key_in_query_string_still_accepted(self):
        # print_server_v2.exe builds deployed before the header existed send ?secret_key=
        response = self.get_jobs(secret_key='barrow-key', location='Barrow')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['location'], 'Barrow')
        self.assertEqual(self.unprinted_locations(), {'Chelsea', 'Greenwich'})

    def test_invalid_header_key_is_rejected(self):
        response = self.get_jobs(headers={'X-Print-Server-Key': 'wrong-key'})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.unprinted_locations(), {'Chelsea', 'Greenwich', 'Barrow'})

    def test_header_takes_precedence_over_query_string(self):
        response = self.get_jobs(headers={'X-Print-Server-Key': 'wrong-key'}, secret_key='chelsea-key')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.unprinted_locations(), {'Chelsea', 'Greenwich', 'Barrow'})

    @override_settings(GREENWICH_PRINT_SERVER_SECRET_KEY='')
    def test_empty_header_does_not_match_unset_server_key(self):
        for header in ['', '  ']:
            response = self.get_jobs(headers={'X-Print-Server-Key': header})
            self.assertEqual(response.status_code, 403)
        self.assertEqual(self.unprinted_locations(), {'Chelsea', 'Greenwich', 'Barrow'})
