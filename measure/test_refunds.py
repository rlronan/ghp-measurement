import decimal
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from .models import Piece, Ledger, Account
from .tests import make_ghp_user

D = decimal.Decimal


class RefundPieceViewTests(TestCase):
    """refund_view must refund at most what was charged for a piece, once, under the right fee type."""

    def setUp(self):
        self.user = make_ghp_user('refund@example.com')
        staff = User.objects.create_superuser('staff', 'staff@example.com', 'pw')
        self.client.force_login(staff)

    def make_piece(self, *fees):
        # bulk_create skips Piece.save(), so the fee ledgers are exactly the ones given here
        piece = Piece.objects.bulk_create([
            Piece(ghp_user=self.user, ghp_user_piece_id=1, length=4, width=4, height=4,
                  bisque_temp='06', glaze_temp='10', price=D('3.84')),
        ])[0]
        for transaction_type, amount in fees:
            Ledger.objects.create(ghp_user=self.user, piece=piece, amount=D(amount), transaction_type=transaction_type)
        return piece

    def url(self, piece):
        return reverse('measure:refund_piece', args=(self.user.pk, piece.ghp_user_piece_id))

    def get_form(self, piece):
        response = self.client.get(self.url(piece), secure=True)
        self.assertEqual(response.status_code, 200)
        return response.context['form']

    def page_post_data(self, piece, firing=True, glazing=True):
        # What a browser submits for the refund page as rendered, with the given boxes ticked
        form = self.get_form(piece)
        values = {bf.name: bf.value() for bf in form}
        data = {name: '' if values[name] is None else str(values[name])
                for name in ['ghp_user', 'piece', 'firing_fee_refund', 'glazing_fee_refund', 'transaction_type', 'note']}
        amount = D('0.00')
        if firing:
            data['firing_fee_check'] = 'on'
            amount += D(values['firing_fee_refund'])
        if glazing:
            data['glazing_fee_check'] = 'on'
            amount += D(values['glazing_fee_refund'])
        data['amount'] = str(amount)
        return data

    def post(self, piece, data):
        return self.client.post(self.url(piece), data, secure=True)

    def balance(self):
        return Account.objects.get(ghp_user=self.user).balance

    def refunds(self, piece):
        return list(Ledger.objects.filter(piece=piece, transaction_type__startswith='auto_refund')
                    .order_by('transaction_id').values_list('transaction_type', 'amount'))

    def test_full_refund_credits_both_fees(self):
        piece = self.make_piece(('auto_bisque_fee', '-1.92'), ('auto_glaze_fee', '-1.92'))
        response = self.post(piece, self.page_post_data(piece))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(sorted(self.refunds(piece)),
                         [('auto_refund_bisque_fee', D('1.92')), ('auto_refund_glaze_fee', D('1.92'))])
        self.assertEqual(self.balance(), D('0.00'))

    def test_page_renders_amounts_and_browser_submission_without_them_works(self):
        piece = self.make_piece(('auto_bisque_fee', '-1.92'), ('auto_glaze_fee', '-1.92'))
        html = self.client.get(self.url(piece), secure=True).content.decode()
        self.assertInHTML('<input type="number" name="firing_fee_refund" value="1.92" step="0.01" '
                          'readonly required id="id_firing_fee_refund" disabled>', html)
        # Browsers do not submit disabled inputs, so the refund amounts are absent from the POST
        data = self.page_post_data(piece)
        for name in ['firing_fee_refund', 'glazing_fee_refund', 'amount']:
            del data[name]
        self.assertEqual(self.post(piece, data).status_code, 302)
        self.assertEqual(self.balance(), D('0.00'))

    def test_resubmitting_refund_does_not_credit_twice(self):
        piece = self.make_piece(('auto_bisque_fee', '-1.92'), ('auto_glaze_fee', '-1.92'))
        data = self.page_post_data(piece)
        self.assertEqual(self.post(piece, data).status_code, 302)
        # e.g. a double-click, a browser resubmit, or a second tab left open on the old page
        response = self.post(piece, data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].non_field_errors())
        self.assertEqual(self.balance(), D('0.00'))
        self.assertEqual(sum(amount for _, amount in self.refunds(piece)), D('3.84'))

    def test_glaze_refund_after_bisque_refund_is_recorded_as_glaze(self):
        piece = self.make_piece(('auto_bisque_fee', '-1.92'), ('auto_glaze_fee', '-1.92'))
        self.assertEqual(self.post(piece, self.page_post_data(piece, glazing=False)).status_code, 302)
        # Come back later and submit the page as offered (both boxes ticked by default)
        self.assertEqual(self.post(piece, self.page_post_data(piece)).status_code, 302)
        self.assertEqual(self.refunds(piece),
                         [('auto_refund_bisque_fee', D('1.92')), ('auto_refund_glaze_fee', D('1.92'))])
        self.assertEqual(self.balance(), D('0.00'))
        form = self.get_form(piece)
        self.assertEqual(form['firing_fee_refund'].value(), D('0.00'))
        self.assertEqual(form['glazing_fee_refund'].value(), D('0.00'))

    def test_posted_refund_amounts_cannot_exceed_fees_charged(self):
        piece = self.make_piece(('auto_bisque_fee', '-1.92'), ('auto_glaze_fee', '-1.92'))
        data = self.page_post_data(piece, glazing=False)
        data.update(firing_fee_refund='500.00', amount='500.00')
        self.post(piece, data)
        self.assertEqual(self.refunds(piece), [('auto_refund_bisque_fee', D('1.92'))])
        self.assertEqual(self.balance(), D('-1.92'))

        data = self.page_post_data(piece)
        data.update(firing_fee_refund='500.00', glazing_fee_refund='500.00', amount='1000.00')
        self.post(piece, data)
        self.assertEqual(self.refunds(piece),
                         [('auto_refund_bisque_fee', D('1.92')), ('auto_refund_glaze_fee', D('1.92'))])
        self.assertEqual(self.balance(), D('0.00'))

    def test_invalid_submission_does_not_create_any_refund(self):
        piece = self.make_piece(('auto_bisque_fee', '-1.92'), ('auto_glaze_fee', '-1.92'))
        data = self.page_post_data(piece)
        data['note'] = 'x' * 1001  # over Ledger.note's max_length
        response = self.post(piece, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('note', response.context['form'].errors)
        self.assertEqual(self.refunds(piece), [])
        self.assertEqual(self.balance(), D('-3.84'))

    def test_previously_mislabeled_glaze_refund_is_not_offered_again(self):
        # Before this fix a glaze refund could be saved as auto_refund_bisque_fee. The total
        # already refunded must still count, whatever type it was saved under.
        piece = self.make_piece(('auto_bisque_fee', '-1.92'), ('auto_glaze_fee', '-1.92'),
                                ('auto_refund_bisque_fee', '1.92'), ('auto_refund_bisque_fee', '1.92'))
        form = self.get_form(piece)
        self.assertEqual(form['firing_fee_refund'].value(), D('0.00'))
        self.assertEqual(form['glazing_fee_refund'].value(), D('0.00'))
        response = self.post(piece, self.page_post_data(piece))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.balance(), D('0.00'))

    def test_piece_with_small_addon_fee_can_be_refunded(self):
        # A bisque-only piece of 20 cubic inches costs the $1.00 minimum (firing alone is $0.60).
        # Adding a glaze later raises the price to $1.20, so the edit charges a $0.20 add-on.
        piece = Piece(ghp_user=self.user, length=D('2.0'), width=D('2.0'), height=D('5.0'),
                      bisque_temp='06', glaze_temp='None')
        piece.clean()
        piece.save()
        piece = Piece.objects.get(pk=piece.pk)
        piece.glaze_temp = '10'
        piece.clean()
        piece.save()
        self.assertEqual(sorted(Ledger.objects.filter(piece=piece).values_list('transaction_type', 'amount')),
                         [('auto_bisque_fee', D('-1.00')), ('auto_glaze_fee', D('-0.20'))])

        form = self.get_form(piece)
        self.assertEqual(form['firing_fee_refund'].value(), D('1.00'))
        self.assertEqual(form['glazing_fee_refund'].value(), D('0.20'))
        self.assertEqual(self.post(piece, self.page_post_data(piece)).status_code, 302)
        self.assertEqual(sorted(self.refunds(piece)),
                         [('auto_refund_bisque_fee', D('1.00')), ('auto_refund_glaze_fee', D('0.20'))])
        self.assertEqual(self.balance(), D('0.00'))
