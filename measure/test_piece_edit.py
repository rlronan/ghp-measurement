from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase, TransactionTestCase
import decimal
from unittest import mock
from django.urls import reverse
from .models import GHPUser, Account, Piece, Ledger, PieceReceipt
from .tests import make_ghp_user

D = decimal.Decimal

# A 4x4x4 piece with 2 handles, for a member: firing = glazing = 64 * 0.03 = $1.92,
# handles = 2 * $0.10. Bisque-only costs $2.12; adding a glaze later costs $1.92 more.
BISQUE_ONLY_PRICE = D('2.12')
GLAZE_ADD_ON = D('1.92')


def piece_post_data(user, length=4, width=4, height=4, handles=2, bisque='06', glaze=None, **overrides):
    data = {
        'ghp_user': user.pk,
        'ghp_user_piece_id': 1,
        'piece_location': 'Chelsea',
        'length': length,
        'width': width,
        'height': height,
        'handles': handles,
        'bisque_temp': bisque or 'None',
        'glaze_temp': glaze or 'None',
        'bisque_temp_checkboxes': [bisque] if bisque else [],
        'glaze_temp_checkboxes': [glaze] if glaze else [],
        'size': 0,
        'price': 0,
        'firing_price': 0,
        'glazing_price': 0,
        'firing_price_per_cubic_inch': '0.03',
        'glazing_price_per_cubic_inch': '0.03',
        'course_number': 'W7',
        'note': '',
        'quantity': 1,
    }
    data.update(overrides)
    return data


class PieceEditHelpers:

    def setUp(self):
        self.user = make_ghp_user('editor@example.com')
        self.client.force_login(self.user)

    def balance(self):
        return Account.objects.get(ghp_user=self.user).balance

    def credit(self, amount):
        Ledger.objects.create(ghp_user=self.user, amount=D(amount), transaction_type='manual_gh_add_misc_credit')

    def create_piece(self, **kwargs):
        response = self.client.post(reverse('measure:piece', args=(self.user.pk,)),
                                    piece_post_data(self.user, **kwargs), secure=True)
        self.assertEqual(response.status_code, 302, getattr(response, 'context', None) and response.context['form'].errors)
        return Piece.objects.get(ghp_user=self.user, ghp_user_piece_id=Piece.objects.filter(ghp_user=self.user).count())

    def edit_piece(self, piece, **kwargs):
        # The edit form is pre-filled from the piece; send the piece's own values unless overridden.
        defaults = dict(length=piece.length, width=piece.width, height=piece.height, handles=piece.handles,
                        bisque=None if piece.bisque_temp == 'None' else piece.bisque_temp,
                        glaze=None if piece.glaze_temp == 'None' else piece.glaze_temp)
        overrides = {k: kwargs.pop(k) for k in list(kwargs) if k not in defaults}
        defaults.update(kwargs)
        data = piece_post_data(self.user, **defaults, **overrides)
        data['ghp_user_piece_id'] = piece.ghp_user_piece_id
        return self.client.post(reverse('measure:modify_piece', args=(self.user.pk, piece.ghp_user_piece_id)),
                                data, secure=True)

    def fees(self):
        return -sum(Ledger.objects.filter(ghp_user=self.user, amount__lt=0).values_list('amount', flat=True))

    def set_balance(self, target):
        Ledger.objects.create(ghp_user=self.user, amount=D(target) - self.balance(),
                              transaction_type='manual_gh_add_misc_charge')
        self.assertEqual(self.balance(), D(target))


class PieceEditTestBase(PieceEditHelpers, TestCase):
    pass


class EditChargesDifferenceTests(PieceEditTestBase):
    """Editing a piece must keep what was already paid, so a later glaze add-on charges only the difference."""

    def test_note_edit_then_glaze_charges_only_glaze(self):
        self.credit('50.00')
        piece = self.create_piece()
        self.assertEqual(self.fees(), BISQUE_ONLY_PRICE)

        response = self.edit_piece(piece, note='just a note')
        self.assertEqual(response.status_code, 302)
        piece.refresh_from_db()
        self.assertEqual(piece.handles, 2)
        self.assertEqual(piece.paid_price, BISQUE_ONLY_PRICE)
        self.assertEqual(self.fees(), BISQUE_ONLY_PRICE)

        response = self.edit_piece(piece, glaze='6')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.fees(), BISQUE_ONLY_PRICE + GLAZE_ADD_ON)
        self.assertEqual(self.balance(), D('50.00') - BISQUE_ONLY_PRICE - GLAZE_ADD_ON)


class PaidPricePersistsTests(PieceEditTestBase):
    """The new paid_price set by an edit that adds a charge must reach the database and the receipt."""

    def test_glaze_add_on_updates_paid_price_and_receipt(self):
        self.credit('50.00')
        piece = self.create_piece()
        response = self.edit_piece(piece, glaze='6')
        self.assertEqual(response.status_code, 302)
        piece.refresh_from_db()
        self.assertEqual(piece.paid_price, BISQUE_ONLY_PRICE + GLAZE_ADD_ON)
        self.assertEqual(self.fees(), BISQUE_ONLY_PRICE + GLAZE_ADD_ON)
        glaze_receipt = PieceReceipt.objects.get(piece=piece, receipt_type='Glaze')
        self.assertEqual(glaze_receipt.price, BISQUE_ONLY_PRICE + GLAZE_ADD_ON)

        # Re-saving after the add-on charges nothing more.
        response = self.edit_piece(piece, note='after glazing')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.fees(), BISQUE_ONLY_PRICE + GLAZE_ADD_ON)

    def test_admin_glaze_change_updates_paid_price(self):
        self.credit('50.00')
        piece = self.create_piece()
        admin = User.objects.create_superuser('desk', 'desk@example.com', 'pw')
        self.client.force_login(admin)
        response = self.client.post(reverse('admin:measure_piece_change', args=(piece.pk,)),
                                    {'glaze_temp': '6'}, secure=True)
        self.assertEqual(response.status_code, 302)
        piece.refresh_from_db()
        self.assertEqual(piece.glaze_temp, '6')
        self.assertEqual(piece.paid_price, BISQUE_ONLY_PRICE + GLAZE_ADD_ON)
        self.assertEqual(self.fees(), BISQUE_ONLY_PRICE + GLAZE_ADD_ON)
        self.assertEqual(PieceReceipt.objects.get(piece=piece, receipt_type='Glaze').price,
                         BISQUE_ONLY_PRICE + GLAZE_ADD_ON)


class EditCannotChangeDimensionsTests(PieceEditTestBase):
    """The edit form shows dimensions and handles read-only; the server must ignore submitted values."""

    def test_shrunk_dimensions_are_ignored(self):
        self.credit('100.00')
        piece = self.create_piece(length=10, width=10, height=10, handles=0)
        self.assertEqual(self.fees(), D('30.00'))
        response = self.edit_piece(piece, length='0.5', width='0.5', height='3', handles=0, glaze='6')
        self.assertEqual(response.status_code, 302)
        piece.refresh_from_db()
        self.assertEqual((piece.length, piece.width, piece.height), (D('10.0'), D('10.0'), D('10.0')))
        self.assertEqual(piece.size, D('1000.00'))
        self.assertEqual(piece.glazing_price, D('30.00'))
        self.assertEqual(self.fees(), D('60.00'))

    def test_changed_handles_are_ignored(self):
        self.credit('50.00')
        piece = self.create_piece()
        response = self.edit_piece(piece, handles=9, note='more handles?')
        self.assertEqual(response.status_code, 302)
        piece.refresh_from_db()
        self.assertEqual(piece.handles, 2)
        self.assertEqual(piece.price, BISQUE_ONLY_PRICE)

    def test_edit_page_renders_dimensions_disabled(self):
        piece = self.create_piece()
        response = self.client.get(reverse('measure:modify_piece', args=(self.user.pk, piece.ghp_user_piece_id)), secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].fields['length'].disabled)
        self.assertInHTML('<input type="number" name="length" value="4.0" step="0.1" readonly required disabled id="id_length">',
                          response.content.decode())


class BlankInputTests(PieceEditTestBase):
    """Blank or out-of-range numeric inputs must come back as form errors, not server errors."""

    def assert_create_rejected(self, field):
        data = piece_post_data(self.user)
        data[field] = ''
        response = self.client.post(reverse('measure:piece', args=(self.user.pk,)), data, secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(field, response.context['form'].errors)
        self.assertFalse(Piece.objects.filter(ghp_user=self.user).exists())

    def test_create_blank_length(self):
        self.assert_create_rejected('length')

    def test_create_blank_width(self):
        self.assert_create_rejected('width')

    def test_create_blank_height(self):
        self.assert_create_rejected('height')

    def test_create_blank_handles(self):
        self.assert_create_rejected('handles')

    def test_create_blank_quantity(self):
        self.assert_create_rejected('quantity')

    def test_create_zero_or_negative_length(self):
        for length in ['0', '-1']:
            response = self.client.post(reverse('measure:piece', args=(self.user.pk,)),
                                        piece_post_data(self.user, length=length), secure=True)
            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.context['form'].is_valid())
            self.assertFalse(Piece.objects.filter(ghp_user=self.user).exists())

    def test_edit_blank_dimensions_and_handles(self):
        self.credit('50.00')
        piece = self.create_piece()
        response = self.edit_piece(piece, length='', width='', height='', handles='', note='blank')
        self.assertEqual(response.status_code, 302)
        piece.refresh_from_db()
        self.assertEqual((piece.length, piece.width, piece.height, piece.handles), (D('4.0'), D('4.0'), D('4.0'), 2))
        self.assertEqual(piece.note, 'blank')


class EditBalanceLimitTests(PieceEditTestBase):
    """The -$25 limit on an edit must be checked against what the edit will charge, not the piece's full price."""

    def test_free_edit_allowed_near_limit(self):
        piece = self.create_piece()
        self.set_balance('-24.00')
        response = self.edit_piece(piece, note='no charge')
        self.assertEqual(response.status_code, 302)
        piece.refresh_from_db()
        self.assertEqual(piece.note, 'no charge')
        self.assertEqual(self.balance(), D('-24.00'))

    def test_free_edit_allowed_below_limit(self):
        # An edit that charges nothing doesn't lower the balance, so the limit doesn't apply.
        piece = self.create_piece()
        self.set_balance('-33.84')
        response = self.edit_piece(piece, note='no charge')
        self.assertEqual(response.status_code, 302)
        piece.refresh_from_db()
        self.assertEqual(piece.note, 'no charge')
        self.assertEqual(self.balance(), D('-33.84'))

    def test_add_on_within_limit_allowed(self):
        piece = self.create_piece()
        self.set_balance('-23.00')
        response = self.edit_piece(piece, glaze='6')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.balance(), D('-23.00') - GLAZE_ADD_ON)

    def test_add_on_past_limit_blocked(self):
        piece = self.create_piece()
        self.set_balance('-24.00')
        response = self.edit_piece(piece, glaze='6')
        self.assertEqual(response.status_code, 200)
        self.assertIn('balance_too_low', [e.code for e in response.context['form'].non_field_errors().as_data()])
        piece.refresh_from_db()
        self.assertEqual(piece.glaze_temp, 'None')
        self.assertEqual(self.balance(), D('-24.00'))


class PostedOwnerDoesNotSetPriceTests(PieceEditTestBase):
    """Posting a staff member's id in the hidden ghp_user field must not price the piece at staff rates."""

    def setUp(self):
        super().setUp()
        self.staff_member = make_ghp_user('staffer@example.com')
        GHPUser.objects.filter(pk=self.staff_member.pk).update(current_ghp_staff=True)
        self.credit('50.00')

    def test_create(self):
        data = piece_post_data(self.user, glaze='6')
        data['ghp_user'] = self.staff_member.pk
        response = self.client.post(reverse('measure:piece', args=(self.user.pk,)), data, secure=True)
        self.assertEqual(response.status_code, 302)
        piece = Piece.objects.get(ghp_user=self.user)
        self.assertEqual(piece.paid_price, BISQUE_ONLY_PRICE + GLAZE_ADD_ON)
        self.assertEqual(self.fees(), BISQUE_ONLY_PRICE + GLAZE_ADD_ON)

    def test_edit(self):
        piece = self.create_piece()
        response = self.edit_piece(piece, glaze='6', ghp_user=self.staff_member.pk)
        self.assertEqual(response.status_code, 302)
        piece.refresh_from_db()
        self.assertEqual(piece.glazing_price, GLAZE_ADD_ON)
        self.assertEqual(self.fees(), BISQUE_ONLY_PRICE + GLAZE_ADD_ON)


class ConcurrentEditTests(PieceEditHelpers, TransactionTestCase):
    """Two submissions of the same add-on (e.g. a double-click) must charge it once.

    SQLite ignores select_for_update, so these tests can't run two requests against a real
    row lock. They check that the view locks the piece inside its own transaction and then
    works from the freshly read row; the lock itself only blocks on Postgres.
    """

    def test_repeated_glaze_submission_charges_once(self):
        self.credit('50.00')
        piece = self.create_piece()
        self.assertEqual(self.edit_piece(piece, glaze='6').status_code, 302)
        self.assertEqual(self.edit_piece(piece, glaze='6').status_code, 302)
        self.assertEqual(self.fees(), BISQUE_ONLY_PRICE + GLAZE_ADD_ON)

    def test_edit_waits_for_lock_then_sees_other_edit(self):
        piece = self.create_piece()
        self.set_balance('-24.00')
        lock_calls = []

        def other_request_commits_first(*args, **kwargs):
            # Stands in for another request that added the glaze and committed while this
            # one waited for the row lock (here staff in the admin, which has no balance limit).
            lock_calls.append(connection.in_atomic_block)
            other = Piece.objects.get(pk=piece.pk)
            other.glaze_temp = '6'
            other.clean()
            other.save()
            return Piece.objects.get_queryset().select_for_update(*args, **kwargs)

        with mock.patch.object(Piece.objects, 'select_for_update', side_effect=other_request_commits_first):
            response = self.edit_piece(piece, glaze='6')
        self.assertEqual(lock_calls, [True])
        # The glaze was already paid for, so this edit charges nothing and isn't blocked. A form
        # built from the piece as read before the lock would see a $1.92 charge taking the
        # -$24.00 balance it was given past the limit, and refuse the edit.
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Ledger.objects.filter(piece=piece, transaction_type='auto_glaze_fee').count(), 1)
        self.assertEqual(self.balance(), D('-24.00') - GLAZE_ADD_ON)
