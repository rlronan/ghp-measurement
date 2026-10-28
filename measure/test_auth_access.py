from urllib.parse import quote

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import GHPUser
from .tests import make_ghp_user


PASSWORD = 'Kiln-Glaze-4471'


def make_imported_ghp_user(username, email):
    # Admin import keys on the username column, so an imported account's username
    # need not equal its email, nor be lowercase.
    user = GHPUser.objects.create(username=username, email=email, first_name='Imported', last_name='Potter')
    return GHPUser.objects.get(pk=user.pk)


class OtherMemberPageTests(TestCase):
    """A member opening another member's page is sent to login; staff can open it."""

    def setUp(self):
        self.member = make_ghp_user('member@example.com')
        self.other = make_ghp_user('other@example.com')

    def member_pages(self):
        return [
            reverse('measure:ghp_user_account_view', args=(self.other.pk,)),
            reverse('measure:piece', args=(self.other.pk,)),
            reverse('measure:modify_piece', args=(self.other.pk, 1)),
            reverse('measure:modify_location', args=(self.other.pk,)),
        ]

    def test_member_is_redirected_to_login_with_next(self):
        self.client.force_login(self.member)
        for url in self.member_pages():
            with self.subTest(url=url):
                response = self.client.get(url, secure=True)
                expected = reverse('measure:login') + '?next=' + quote(url)
                self.assertRedirects(response, expected, fetch_redirect_response=False)

    def test_staff_can_open_member_account_page(self):
        self.client.force_login(User.objects.create_superuser('staff', 'staff@example.com', PASSWORD))
        url = reverse('measure:ghp_user_account_view', args=(self.other.pk,))
        self.assertEqual(self.client.get(url, secure=True).status_code, 200)


class PageOwnershipTests(TestCase):
    """Page ownership is decided by account identity, not by comparing a username to an email."""

    def pieces_page(self, ghp_user):
        return self.client.get(reverse('measure:ghp_user_piece_view', args=(ghp_user.pk,)), secure=True)

    def test_imported_member_with_username_unlike_email_can_open_own_page(self):
        member = make_imported_ghp_user('jdoe', 'jdoe@example.com')
        self.client.force_login(member)
        self.assertEqual(self.pieces_page(member).status_code, 200)

    def test_username_equal_to_another_members_email_grants_nothing(self):
        victim = make_imported_ghp_user('victim', 'victim@example.com')
        attacker = make_imported_ghp_user('victim@example.com', 'attacker@example.com')
        self.client.force_login(attacker)
        response = self.pieces_page(victim)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('measure:login')))


class RegistrationTests(TestCase):

    def register(self, email):
        return self.client.post(reverse('measure:register'), {
            'first_name': 'Jane', 'last_name': 'Potter', 'email': email, 'username': '',
            'consent': 'on', 'password1': PASSWORD, 'password2': PASSWORD,
        }, secure=True)

    def test_valid_registration_creates_lowercase_account(self):
        response = self.register('New.Member@Example.com')
        self.assertEqual(response.status_code, 302)
        user = GHPUser.objects.get()
        self.assertEqual((user.username, user.email), ('new.member@example.com', 'new.member@example.com'))

    def test_email_without_domain_suffix_is_a_form_error(self):
        response = self.register('jane@gmail')
        self.assertEqual(response.status_code, 200)
        self.assertIn('email', response.context['form'].errors)
        self.assertFalse(GHPUser.objects.exists())

    def test_email_differing_only_in_case_is_rejected(self):
        make_imported_ghp_user('Jane@Example.com', 'Jane@Example.com')
        response = self.register('jane@example.com')
        self.assertEqual(response.status_code, 200)
        self.assertIn('email', response.context['form'].errors)
        self.assertEqual(GHPUser.objects.count(), 1)

    def test_email_matching_another_accounts_username_is_rejected(self):
        make_imported_ghp_user('Jane@Example.com', 'jane.other@example.com')
        response = self.register('jane@example.com')
        self.assertEqual(response.status_code, 200)
        self.assertIn('email', response.context['form'].errors)
        self.assertEqual(GHPUser.objects.count(), 1)


class CaseInsensitiveLoginTests(TestCase):

    def make_user_with_password(self, username):
        user = make_imported_ghp_user(username, username)
        user.set_password(PASSWORD)
        user.save()
        return user

    def post_login(self, username):
        return self.client.post(reverse('measure:login'), {'username': username, 'password': PASSWORD}, secure=True)

    def logged_in_pk(self):
        return self.client.session.get('_auth_user_id')

    def test_mixed_case_username_logs_in_with_lowercase_email(self):
        user = self.make_user_with_password('Jane@Example.com')
        self.assertEqual(self.post_login('jane@example.com').status_code, 302)
        self.assertEqual(self.logged_in_pk(), str(user.pk))

    def test_wrong_password_still_fails(self):
        self.make_user_with_password('Jane@Example.com')
        response = self.client.post(reverse('measure:login'),
                                    {'username': 'jane@example.com', 'password': 'wrong-password'}, secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(self.logged_in_pk())

    def test_existing_case_duplicates_do_not_crash_and_exact_match_wins(self):
        self.make_user_with_password('Jane@Example.com')
        lower = self.make_user_with_password('jane@example.com')
        # Ambiguous: no exact match, two case-insensitive matches. Refuse rather than guess.
        response = self.post_login('JANE@EXAMPLE.COM')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(self.logged_in_pk())
        # An exact match is unambiguous and behaves as before.
        self.assertEqual(self.post_login('jane@example.com').status_code, 302)
        self.assertEqual(self.logged_in_pk(), str(lower.pk))
