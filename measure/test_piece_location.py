from django.test import TestCase
from django.urls import reverse
from .models import Piece, PieceReceipt
from .test_piece_edit import piece_post_data
from .tests import make_ghp_user
from .views import PIECE_LOCATION_COOKIE


class PieceLocationDefaultTests(TestCase):
    """The measure-a-piece page defaults to the location last chosen on the same browser."""

    def setUp(self):
        self.user = make_ghp_user('location@example.com')
        self.user.current_location = 'Greenwich'
        self.user.save()
        self.client.force_login(self.user)
        self.url = reverse('measure:piece', args=(self.user.pk,))

    def initial_location(self):
        response = self.client.get(self.url, secure=True)
        self.assertEqual(response.status_code, 200)
        return response.context['form'].fields['piece_location'].initial

    def test_without_cookie_defaults_to_saved_location(self):
        self.assertEqual(self.initial_location(), 'Greenwich')

    def test_submitting_a_piece_remembers_its_location(self):
        response = self.client.post(self.url, piece_post_data(self.user, piece_location='Barrow'), secure=True)
        self.assertEqual(response.status_code, 302)
        cookie = response.cookies[PIECE_LOCATION_COOKIE]
        self.assertEqual(cookie.value, 'Barrow')
        self.assertTrue(cookie['httponly'])
        self.assertTrue(cookie['secure'])
        self.assertEqual(cookie['samesite'], 'Lax')
        self.assertGreater(int(cookie['max-age']), 0)
        self.assertEqual(PieceReceipt.objects.get().piece_location, 'Barrow')
        self.assertEqual(self.initial_location(), 'Barrow')

    def test_cookie_applies_to_other_members_on_same_browser(self):
        # A studio computer is shared: the next member measuring there gets the same default
        self.client.cookies[PIECE_LOCATION_COOKIE] = 'Barrow'
        other = make_ghp_user('other@example.com')
        other.current_location = 'Chelsea'
        other.save()
        self.client.force_login(other)
        response = self.client.get(reverse('measure:piece', args=(other.pk,)), secure=True)
        self.assertEqual(response.context['form'].fields['piece_location'].initial, 'Barrow')

    def test_unknown_cookie_value_is_ignored(self):
        for value in ['Narnia', '', 'None', 'Both']:
            self.client.cookies[PIECE_LOCATION_COOKIE] = value
            self.assertEqual(self.initial_location(), 'Greenwich')

    def test_invalid_submission_does_not_set_cookie(self):
        data = piece_post_data(self.user, piece_location='Barrow', length='')
        response = self.client.post(self.url, data, secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(PIECE_LOCATION_COOKIE, response.cookies)
        self.assertFalse(Piece.objects.exists())

    def test_posted_location_still_wins_over_cookie(self):
        self.client.cookies[PIECE_LOCATION_COOKIE] = 'Barrow'
        response = self.client.post(self.url, piece_post_data(self.user, piece_location='Chelsea'), secure=True)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(PieceReceipt.objects.get().piece_location, 'Chelsea')
        self.assertEqual(response.cookies[PIECE_LOCATION_COOKIE].value, 'Chelsea')
