import decimal

import tablib
from django.contrib.auth.models import User
from django.db import connection
from django.db.models import Sum
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from .admin import GHPUserResource
from .models import GHPUser, Account, PlaceholderAccount, Piece, Ledger, PieceReceipt
from .tests import make_ghp_user


def make_piece(user, piece_id=1, location='Chelsea'):
    # bulk_create skips Piece.save(), which does pricing/ledger work irrelevant here
    return Piece.objects.bulk_create([
        Piece(ghp_user=user, ghp_user_piece_id=piece_id, length=4, width=4, height=4, piece_location=location),
    ])[0]


def make_receipt(piece, **overrides):
    fields = dict(piece=piece, ghp_user_name='Test Potter', receipt_type='Bisque',
                  length=4, width=4, height=4, price=decimal.Decimal('5.00'),
                  piece_location=piece.piece_location)
    fields.update(overrides)
    return PieceReceipt.objects.create(**fields)


def ledger_sum(user):
    return Ledger.objects.filter(ghp_user=user).aggregate(total=Sum('amount'))['total'] or decimal.Decimal('0.00')


class StaffAdminTestCase(TestCase):
    def setUp(self):
        staff = User.objects.create_superuser('staff', 'staff@example.com', 'pw')
        self.client.force_login(staff)


class AdminDeleteBlockedTests(StaffAdminTestCase):
    """The per-object Delete button must not be able to break balance == sum(ledger)."""

    def setUp(self):
        super().setUp()
        self.user = make_ghp_user('delete@example.com')
        self.piece = make_piece(self.user)
        self.ledger = Ledger.objects.create(ghp_user=self.user, piece=self.piece, amount=decimal.Decimal('-5.00'),
                                            transaction_type='manual_gh_add_misc_charge')

    def post_delete(self, model, pk):
        return self.client.post(reverse(f'admin:measure_{model}_delete', args=(pk,)), {'post': 'yes'}, secure=True)

    def test_ledger_cannot_be_deleted(self):
        response = self.post_delete('ledger', self.ledger.pk)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Ledger.objects.filter(pk=self.ledger.pk).exists())
        self.assertEqual(Account.objects.get(ghp_user=self.user).balance, ledger_sum(self.user))

    def test_account_cannot_be_deleted(self):
        response = self.post_delete('account', self.user.pk)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Account.objects.get(ghp_user=self.user).balance, decimal.Decimal('-5.00'))

    def test_piece_cannot_be_deleted(self):
        response = self.post_delete('piece', self.piece.pk)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Piece.objects.filter(pk=self.piece.pk).exists())

    def test_change_pages_show_no_delete_link(self):
        for model, pk in [('ledger', self.ledger.pk), ('account', self.user.pk), ('piece', self.piece.pk)]:
            response = self.client.get(reverse(f'admin:measure_{model}_change', args=(pk,)), secure=True)
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, reverse(f'admin:measure_{model}_delete', args=(pk,)))


class LedgerWithoutUserTests(StaffAdminTestCase):
    """A ledger row whose user was deleted (ghp_user is SET_NULL) must still render."""

    def setUp(self):
        super().setUp()
        user = make_ghp_user('orphan@example.com')
        self.ledger = Ledger.objects.create(ghp_user=user, amount=decimal.Decimal('10.00'),
                                            transaction_type='manual_gh_add_misc_credit', note='orphaned')
        Ledger.objects.filter(pk=self.ledger.pk).update(ghp_user=None)
        self.ledger.refresh_from_db()

    def test_str_without_user(self):
        self.assertIn('orphaned', str(self.ledger))

    def test_changelist_and_change_page_render(self):
        response = self.client.get(reverse('admin:measure_ledger_changelist'), secure=True)
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('admin:measure_ledger_change', args=(self.ledger.pk,)), secure=True)
        self.assertEqual(response.status_code, 200)


class PieceReceiptAdminReadOnlyTests(StaffAdminTestCase):
    """A receipt records what was charged; staff may only toggle `printed` to reprint."""

    def setUp(self):
        super().setUp()
        self.user = make_ghp_user('receipt@example.com')
        self.receipt = make_receipt(make_piece(self.user), printed=True)

    def test_change_form_only_changes_printed(self):
        url = reverse('admin:measure_piecereceipt_change', args=(self.receipt.pk,))
        response = self.client.post(url, {
            'ghp_user_name': 'Someone Else', 'piece': self.receipt.piece_id, 'piece_number': 1,
            'length': 9, 'width': 9, 'height': 9, 'handles': 0, 'size': 729, 'price': '0.01',
            'course_number': '', 'bisque_temp': '06', 'glaze_temp': '10', 'receipt_type': 'Glaze',
            'piece_location': 'Barrow', 'printed_date': '', 'number_printed': 0,
            # `printed` omitted from the POST means unchecked
        }, secure=True)
        self.assertEqual(response.status_code, 302)
        self.receipt.refresh_from_db()
        self.assertFalse(self.receipt.printed)
        self.assertEqual(self.receipt.price, decimal.Decimal('5.00'))
        self.assertEqual(self.receipt.length, decimal.Decimal('4.0'))
        self.assertEqual(self.receipt.receipt_type, 'Bisque')
        self.assertEqual(self.receipt.ghp_user_name, 'Test Potter')
        self.assertEqual(self.receipt.piece_location, 'Chelsea')

    def test_receipts_cannot_be_added_or_deleted(self):
        response = self.client.get(reverse('admin:measure_piecereceipt_add'), secure=True)
        self.assertEqual(response.status_code, 403)
        response = self.client.post(reverse('admin:measure_piecereceipt_delete', args=(self.receipt.pk,)),
                                    {'post': 'yes'}, secure=True)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(PieceReceipt.objects.filter(pk=self.receipt.pk).exists())

    def test_reprint_action_still_works(self):
        response = self.client.post(reverse('admin:measure_piecereceipt_changelist'), {
            'action': 'reprint_receipt', '_selected_action': [self.receipt.pk],
        }, secure=True)
        self.assertEqual(response.status_code, 302)
        self.receipt.refresh_from_db()
        self.assertFalse(self.receipt.printed)


class AdminAddFormTests(StaffAdminTestCase):
    """Piece and Account add pages crashed; neither can be created correctly from the admin."""

    def test_piece_add_is_forbidden_not_500(self):
        url = reverse('admin:measure_piece_add')
        self.assertEqual(self.client.get(url, secure=True).status_code, 403)
        self.assertEqual(self.client.post(url, {'glaze_temp': '10'}, secure=True).status_code, 403)

    def test_account_add_is_forbidden_not_500(self):
        url = reverse('admin:measure_account_add')
        self.assertEqual(self.client.get(url, secure=True).status_code, 403)
        self.assertEqual(self.client.post(url, {}, secure=True).status_code, 403)

    def test_changelists_still_render(self):
        user = make_ghp_user('lists@example.com')
        make_piece(user)
        for model in ['piece', 'account']:
            response = self.client.get(reverse(f'admin:measure_{model}_changelist'), secure=True)
            self.assertEqual(response.status_code, 200)


class LedgerAdminAddPieceOwnerTests(StaffAdminTestCase):
    """A ledger row's piece must belong to the ledger row's user."""

    def setUp(self):
        super().setUp()
        self.user = make_ghp_user('owner@example.com')
        self.other = make_ghp_user('not-owner@example.com')
        self.other_piece = make_piece(self.other)
        self.own_piece = make_piece(self.user)

    def post_add(self, piece):
        return self.client.post(reverse('admin:measure_ledger_add'), {
            'ghp_user': self.user.pk, 'amount': '-2.00', 'transaction_type': 'manual_gh_add_misc_charge',
            'piece': piece.pk, 'note': 'test',
        }, secure=True)

    def test_other_users_piece_is_rejected(self):
        response = self.post_add(self.other_piece)
        self.assertEqual(response.status_code, 200)
        self.assertIn('piece', response.context['adminform'].form.errors)
        self.assertFalse(Ledger.objects.exists())
        self.assertEqual(Account.objects.get(ghp_user=self.user).balance, decimal.Decimal('0.00'))

    def test_own_piece_is_accepted(self):
        response = self.post_add(self.own_piece)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Account.objects.get(ghp_user=self.user).balance, decimal.Decimal('-2.00'))


class GHPUserImportValidationTests(TestCase):
    """The GHPUser import must reject rows that registration would never produce."""

    headers = ['first_name', 'last_name', 'username', 'email', 'current_location']

    def run_import(self, *rows):
        dataset = tablib.Dataset(*rows, headers=self.headers)
        return GHPUserResource().import_data(dataset, dry_run=False)

    def assert_rejected(self, row, field):
        result = self.run_import(row)
        self.assertTrue(result.has_validation_errors())
        self.assertIn(field, result.invalid_rows[0].field_specific_errors)
        self.assertFalse(GHPUser.objects.filter(username=row[2]).exists())

    def test_valid_row_creates_user_with_account(self):
        result = self.run_import(['Ada', 'Potter', 'ada@example.com', 'ada@example.com', 'Barrow'])
        self.assertFalse(result.has_validation_errors() or result.has_errors())
        user = GHPUser.objects.get(username='ada@example.com')
        self.assertEqual(user.current_location, 'Barrow')
        self.assertTrue(Account.objects.filter(ghp_user=user).exists())

    def test_invalid_email_is_rejected(self):
        self.assert_rejected(['Ada', 'Potter', 'not-an-email', 'not-an-email', 'Chelsea'], 'email')

    def test_blank_email_is_rejected(self):
        self.assert_rejected(['Ada', 'Potter', 'ada@example.com', '', 'Chelsea'], 'email')

    def test_blank_names_are_rejected(self):
        self.assert_rejected(['', 'Potter', 'ada@example.com', 'ada@example.com', 'Chelsea'], 'first_name')
        self.assert_rejected(['Ada', '', 'ada@example.com', 'ada@example.com', 'Chelsea'], 'last_name')

    def test_username_must_be_lowercased_email(self):
        self.assert_rejected(['Ada', 'Potter', 'someone-else@example.com', 'ada@example.com', 'Chelsea'], 'username')

    def test_unknown_location_is_rejected(self):
        self.assert_rejected(['Ada', 'Potter', 'ada@example.com', 'ada@example.com', 'Brooklyn'], 'current_location')

    def test_duplicate_row_in_file_is_rejected(self):
        result = self.run_import(
            ['Ada', 'Potter', 'ada@example.com', 'ada@example.com', 'Chelsea'],
            ['Ada', 'Typo', 'ada@example.com', 'ada@example.com', 'Barrow'],
        )
        self.assertTrue(result.has_validation_errors())
        self.assertEqual(len(result.invalid_rows), 1)

    def test_email_used_by_another_user_is_rejected(self):
        GHPUser.objects.create(username='legacy-name', email='ada@example.com', first_name='Ada', last_name='Old')
        result = self.run_import(['Ada', 'Potter', 'ada@example.com', 'ada@example.com', 'Chelsea'])
        self.assertTrue(result.has_validation_errors())
        self.assertIn('email', result.invalid_rows[0].field_specific_errors)

    def test_existing_user_can_be_updated(self):
        make_ghp_user('ada@example.com')
        result = self.run_import(['Ada', 'Potter', 'ada@example.com', 'ada@example.com', 'Greenwich'])
        self.assertFalse(result.has_validation_errors() or result.has_errors())
        self.assertEqual(GHPUser.objects.get(username='ada@example.com').current_location, 'Greenwich')


class AdminExportQueryCountTests(StaffAdminTestCase):
    """The admin "Export Selected" actions must not issue queries per exported row."""

    def make_rows(self, n, offset):
        for i in range(n):
            user = make_ghp_user(f'export{offset + i}@example.com')
            piece = make_piece(user)
            make_receipt(piece)
            Ledger.objects.create(ghp_user=user, piece=piece, amount=decimal.Decimal('-5.00'),
                                  transaction_type='manual_gh_add_misc_charge')

    def export_queries(self, model, queryset):
        pks = list(queryset.values_list('pk', flat=True))
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.post(reverse(f'admin:measure_{model}_changelist'), {
                'action': 'export_as_csv', '_selected_action': pks,
            }, secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.content.decode().strip().splitlines()), len(pks) + 1)
        return len(ctx.captured_queries)

    def assert_constant_queries(self, model, queryset):
        self.make_rows(1, 0)
        one = self.export_queries(model, queryset)
        self.make_rows(4, 1)
        five = self.export_queries(model, queryset)
        self.assertEqual(one, five)

    def test_ghpuser_export(self):
        self.assert_constant_queries('ghpuser', GHPUser.objects.all())

    def test_piece_export(self):
        self.assert_constant_queries('piece', Piece.objects.all())

    def test_ledger_export(self):
        self.assert_constant_queries('ledger', Ledger.objects.all())

    def test_ledger_export_location_matches_latest_receipt(self):
        user = make_ghp_user('moved@example.com')
        piece = make_piece(user)
        make_receipt(piece, piece_location='Chelsea')
        make_receipt(piece, piece_location='Barrow')
        Ledger.objects.create(ghp_user=user, piece=piece, amount=decimal.Decimal('-5.00'),
                              transaction_type='manual_gh_add_misc_charge')
        response = self.client.post(reverse('admin:measure_ledger_changelist'), {
            'action': 'export_as_csv', '_selected_action': list(Ledger.objects.values_list('pk', flat=True)),
        }, secure=True)
        self.assertTrue(response.content.decode().strip().splitlines()[1].endswith(',Barrow'))


class PlaceholderBalanceTests(TestCase):
    """A balance carried over from a PlaceholderAccount must be recorded in the ledger."""

    def test_placeholder_balance_has_ledger_row(self):
        for email, amount in [('credit@example.com', '12.50'), ('debt@example.com', '-7.25')]:
            PlaceholderAccount.objects.create(email=email, balance=decimal.Decimal(amount))
            user = make_ghp_user(email)
            self.assertEqual(Account.objects.get(ghp_user=user).balance, decimal.Decimal(amount))
            self.assertEqual(ledger_sum(user), decimal.Decimal(amount))

    def test_zero_placeholder_balance_creates_no_ledger_row(self):
        PlaceholderAccount.objects.create(email='zero@example.com', balance=decimal.Decimal('0.00'))
        user = make_ghp_user('zero@example.com')
        self.assertEqual(Account.objects.get(ghp_user=user).balance, decimal.Decimal('0.00'))
        self.assertFalse(Ledger.objects.filter(ghp_user=user).exists())
