from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic
from django.utils import timezone
from .forms import PieceForm, CreateGHPUserForm, ModifyPieceForm, \
    RefundPieceForm, AddCreditForm, ModifyLocationForm
from .models import GHPUser, Account, Piece, Ledger, PieceReceipt
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm, \
    PasswordResetForm, SetPasswordForm, AuthenticationForm
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import user_passes_test, login_required, permission_required
from django.contrib.auth.models import User
import csv
import numpy as np
import datetime
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import TemplateView
from django.http.response import JsonResponse, HttpResponse
import stripe
import decimal
import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)

# Create your views here.



def user_owns_object_check(user, ghp_user):
    return user.get_username() == ghp_user.get_username()

def user_is_staff_check(user):
    return user.is_staff

def user_can_refund_check(user):
    return user.groups.filter(name='can_refund').exists()

def user_can_add_credit_check(user):
    print("Checking if user is in group can_add_credit")
    print("User: {}".format(user))
    print("User groups: {}".format(user.groups.all()))
    print("User groups filter: {}".format(user.groups.filter(name='can_add_credit').exists()))
    return user.groups.filter(name='can_add_credit').exists()

def robots_txt(request):
    return render(request, 'measure/robots.txt', {})





# @user_passes_test(email_check)

@login_required(login_url='measure:login')
def index_view(request):
    logger.info(f"User {request.user.username} accessing index_view.")
    print("Checking if user has permission to account index page")
    if not user_is_staff_check(request.user):
        print("Requesting user: {}, does not have access to the account index page".format(request.user.get_username()))
        logger.warning(f"User {request.user.username} does not have staff permissions for index_view. Redirecting to login.")
        return redirect(reverse("measure:login"))#/?next=%s" % request.path))

    ghp_user_admins = GHPUser.objects.filter(current_faculty=True).order_by('last_name').all()
    ghp_user_staff = GHPUser.objects.filter(current_ghp_staff=True).order_by('last_name').all()
    ghp_user_students = GHPUser.objects.filter(current_student=True).order_by('last_name').all()
    num_rows = max([ghp_user_admins.count(), ghp_user_staff.count(), ghp_user_students.count()])

    num_rows = list(range(num_rows))
    logger.info(f"Rendering index_view for user {request.user.username} with {ghp_user_admins.count()} admins, {ghp_user_staff.count()} staff, {ghp_user_students.count()} students.")
    return render(request, 'measure/index.html', {
        'num_rows': num_rows,
        'ghp_user_admins': ghp_user_admins,
        'ghp_user_staff': ghp_user_staff,
        'ghp_user_students': ghp_user_students,})

@login_required(login_url='measure:login')
class GHPUserView(generic.DetailView):
    model = GHPUser
    template_name = 'measure/ghp_user.html'
    context_object_name = 'ghp_user_piece_list'

    def get_queryset(self):
        """Return the list of all pieces associated with a ghp_user."""
        logger.info(f"User {self.request.user.username} querying pieces for ghp_user_id: {self.ghp_user_id} in GHPUserView.")
        # Assuming ghp_user_id is passed as a kwarg 'pk' to the view
        ghp_user_id = self.ghp_user_id
        return Piece.objects.filter(ghp_user_id=ghp_user_id).order_by('-date').all()

@login_required(login_url='measure:login')
def ghp_user_piece_view(request, ghp_user_id):
    logger.info(f"User {request.user.username} accessing ghp_user_piece_view for ghp_user_id: {ghp_user_id}.")
    ghp_user = get_object_or_404(GHPUser, pk=ghp_user_id)
    print("Checking if user has permission to view piece overview page")
    if not (user_owns_object_check(request.user, ghp_user) 
            or user_is_staff_check(request.user)):
#    if not request.user.get_username() == ghp_user.get_username():
        # if the user is not the correct user, redirect to the login page
        print("Requesting user: {}, does not have access to ghp_user: {}".format(request.user.get_username(), ghp_user.get_username()))
        logger.warning(f"User {request.user.username} permission denied for ghp_user_piece_view for ghp_user: {ghp_user.get_username()}. Redirecting to login.")
        return redirect(reverse("measure:login"))#/?next=%s" % request.path))

    ghp_user_piece_list = Piece.objects.filter(ghp_user_id=ghp_user_id).order_by('-ghp_user_piece_id').all()
    logger.info(f"Rendering ghp_user_piece_view for user {request.user.username}, ghp_user: {ghp_user.get_username()} with {ghp_user_piece_list.count()} pieces.")
    return render(request, 'measure/ghp_user_pieces.html', {'ghp_user': ghp_user, 'ghp_user_piece_list': ghp_user_piece_list})

@login_required(login_url='measure:login')
def ghp_user_account_view(request, ghp_user_id):
    logger.info(f"User {request.user.username} accessing ghp_user_account_view for ghp_user_id: {ghp_user_id}.")
    ghp_user = get_object_or_404(GHPUser, pk=ghp_user_id)
    print("Checking if user has permission to view account page")
    if not (user_owns_object_check(request.user, ghp_user) 
            or user_is_staff_check(request.user)):
    #if not request.user.get_username() == ghp_user.get_username():
        # if the user is not the correct user, redirect to the login page
        print("Requesting user: {}, does not have access to ghp_user: {}".format(request.user.get_username(), ghp_user.get_username()))
        logger.warning(f"User {request.user.username} permission denied for ghp_user_account_view for ghp_user: {ghp_user.get_username()}. Redirecting to login.")
        return redirect(reverse("measure:login/?next=%s" % request.path))

    ghp_user_account = ghp_user.account #Account.objects.filter(ghp_user=ghp_user).first() # should only be one
    ghp_user_transactions = Ledger.objects.filter(ghp_user=ghp_user).order_by('-ghp_user_transaction_number').all()
    logger.info(f"Rendering ghp_user_account_view for user {request.user.username}, ghp_user: {ghp_user.get_username()} with account balance {ghp_user_account.balance} and {ghp_user_transactions.count()} transactions.")
    return render(request, 'measure/ghp_user_account.html', {
        'ghp_user': ghp_user,
        'ghp_user_account': ghp_user_account,
        'ghp_user_transactions': ghp_user_transactions,
        
    })


@login_required(login_url='measure:login')
def PieceView(request, ghp_user_id):
    logger.info(f"User {request.user.username} accessing PieceView for ghp_user_id: {ghp_user_id}. Request method: {request.method}")
    ghp_user = get_object_or_404(GHPUser, pk=ghp_user_id)
    print("Checking if user has permission to view piece page")
    if not (user_owns_object_check(request.user, ghp_user) 
            or user_is_staff_check(request.user)):
        # if the user is not the correct user, redirect to the login page
        print("Requesting user: {}, does not have access to ghp_user: {}".format(request.user.get_username(), ghp_user.get_username()))
        logger.warning(f"User {request.user.username} permission denied for PieceView for ghp_user: {ghp_user.get_username()}. Redirecting to login.")
        return redirect(reverse("measure:login/?next=%s" % request.path))
    
    user_balance = ghp_user.account.balance #Account.objects.filter(ghp_user=ghp_user).first() # should only be one
    if request.method == 'POST':
        form = PieceForm(request.POST, request.FILES, ghp_user=ghp_user, user_balance=user_balance)
        if form.is_valid():
            logger.info(f"PieceForm is valid for user {request.user.username}, ghp_user: {ghp_user.get_username()}.")
            print("Measuring piece form is valid")
            instance = form.save(commit=False)
            
            instance.save()
            logger.info(f"Piece saved for user {request.user.username}, ghp_user: {ghp_user.get_username()}. Piece ID: {instance.id}")
            # process the data in form.cleaned_data as required
            return HttpResponseRedirect(reverse('measure:ghp_user_piece_view', args=(ghp_user_id,)))
        else:
            logger.warning(f"PieceForm is invalid for user {request.user.username}, ghp_user: {ghp_user.get_username()}. Errors: {form.errors}")
            print("Measuring piece form is not valid")
            print(form.errors)
            return render(request, 'measure/piece.html', {'form': form})

    else:
        form = PieceForm(ghp_user=ghp_user, user_balance=user_balance)
        logger.info(f"Rendering PieceForm (GET request) for user {request.user.username}, ghp_user: {ghp_user.get_username()}.")
    return render(request, 'measure/piece.html', {'form': form})


@login_required(login_url='measure:login')
def ModifyPieceView(request, ghp_user_id, ghp_user_piece_id):
    logger.info(f"User {request.user.username} accessing ModifyPieceView for ghp_user_id: {ghp_user_id}, piece_id: {ghp_user_piece_id}. Request method: {request.method}")
    ghp_user = get_object_or_404(GHPUser, pk=ghp_user_id)
    print("Checking if user has permission to view modify piece page")
    if not (user_owns_object_check(request.user, ghp_user) 
            or user_is_staff_check(request.user)):
        # if the user is not the correct user, redirect to the login page
        print("Requesting user: {}, does not have access to ghp_user: {}".format(request.user.get_username(), ghp_user.get_username()))
        logger.warning(f"User {request.user.username} permission denied for ModifyPieceView for ghp_user: {ghp_user.get_username()}. Redirecting to login.")
        return redirect(reverse("measure:login_view/?next=%s" % request.path))

    piece = Piece.objects.filter(ghp_user=ghp_user).filter(ghp_user_piece_id=ghp_user_piece_id).first()
    if not piece:
        logger.error(f"Piece not found for ghp_user_id: {ghp_user_id}, piece_id: {ghp_user_piece_id} in ModifyPieceView. User: {request.user.username}")
        # Consider returning a 404 or an appropriate error response here
        return HttpResponse("Piece not found", status=404) # Or redirect with a message
    piece_image = piece.image
    user_balance = ghp_user.account.balance
    print("Found user: " + str(ghp_user))
    print("Found piece: {} with pk: {}".format(str(piece), piece.pk))
    print("Found Balance: " + str(user_balance))
    if request.method == 'POST':
        print("POST request")
        form = ModifyPieceForm(request.POST, request.FILES, ghp_user=ghp_user, piece=piece, user_balance=user_balance)# piece_image=piece_image)
        if form.is_valid():
            logger.info(f"ModifyPieceForm is valid for user {request.user.username}, ghp_user: {ghp_user.get_username()}, piece_id: {ghp_user_piece_id}.")
            print("Form is valid")
            form.instance.pk = piece.id
            form.instance.date = piece.date
            instance = form.save(commit=False)
            # process the data in form.cleaned_data as required
            instance.save()
            logger.info(f"Piece modified for user {request.user.username}, ghp_user: {ghp_user.get_username()}, piece_id: {instance.id}.")
            return HttpResponseRedirect(reverse('measure:ghp_user_piece_view', args=(ghp_user_id,)))
        else:
            logger.warning(f"ModifyPieceForm is invalid for user {request.user.username}, ghp_user: {ghp_user.get_username()}, piece_id: {ghp_user_piece_id}. Errors: {form.errors}")
            print("Modify piece form is not valid")
            print(form.errors)
            return render(request, 'measure/modify_piece.html', {'form': form, 'ghp_user': ghp_user, 'piece': piece})

    else:
        print("GET request")
        form = ModifyPieceForm(ghp_user=ghp_user, piece=piece, user_balance=user_balance)
        logger.info(f"Rendering ModifyPieceForm (GET request) for user {request.user.username}, ghp_user: {ghp_user.get_username()}, piece_id: {ghp_user_piece_id}.")
    return render(request, 'measure/modify_piece.html', {'form': form})

@login_required(login_url='measure:login')
def ModifyLocationView(request, ghp_user_id):
    logger.info(f"User {request.user.username} accessing ModifyLocationView for ghp_user_id: {ghp_user_id}. Request method: {request.method}")
    ghp_user = get_object_or_404(GHPUser, pk=ghp_user_id)
    print("Checking if user has permission to view modify location page")
    if not (user_owns_object_check(request.user, ghp_user) 
            or user_is_staff_check(request.user)):
        # if the user is not the correct user, redirect to the login page
        print("Requesting user: {}, does not have access to ghp_user: {}".format(request.user.get_username(), ghp_user.get_username()))
        logger.warning(f"User {request.user.username} permission denied for ModifyLocationView for ghp_user: {ghp_user.get_username()}. Redirecting to login.")
        return redirect(reverse("measure:login_view/?next=%s" % request.path))

    print("Found user: " + str(ghp_user))
    if request.method == 'POST':
        print("POST request")
        form = ModifyLocationForm(request.POST, ghp_user=ghp_user)
        if form.is_valid():
            logger.info(f"ModifyLocationForm is valid for user {request.user.username}, ghp_user: {ghp_user.get_username()}.")
            print("Form is valid")
            instance = form.save(commit=False)
            # process the data in form.cleaned_data as required
            ghp_user.current_location = instance.current_location
            ghp_user.save()
            logger.info(f"Location modified for ghp_user: {ghp_user.get_username()} to {instance.current_location} by user {request.user.username}.")
            return HttpResponseRedirect(reverse('measure:user'))
        else:
            logger.warning(f"ModifyLocationForm is invalid for user {request.user.username}, ghp_user: {ghp_user.get_username()}. Errors: {form.errors}")
            print("Modify Location Form is not valid")
            print(form.errors)
            return render(request, 'measure/modify_location.html', {'form': form, 'ghp_user': ghp_user})

    else:
        print("GET request")
        form = ModifyLocationForm(ghp_user=ghp_user)
        logger.info(f"Rendering ModifyLocationForm (GET request) for user {request.user.username}, ghp_user: {ghp_user.get_username()}.")
    return render(request, 'measure/modify_location.html', {'form': form})


#@unauthenticated_user
def register_page(request):
    logger.info(f"Accessing register_page. Request method: {request.method}")
    if request.method == 'POST':
        form = CreateGHPUserForm(request.POST)
        if form.is_valid():
            logger.info(f"CreateGHPUserForm is valid. Attempting to register user with email: {form.cleaned_data.get('email')}")
            print("Register form is valid")
            instance = form.save(commit=False)
            # process the data in form.cleaned_data as required

            # check if the user is already in the database
            # if so, return a message that the user already exists, and redirect to the login page
            # if not, create the user and redirect to the user's account page
            
            ghp_user_email = instance.email
            ghp_user = GHPUser.objects.filter(email=ghp_user_email).first()
            if ghp_user:
                print("User already exists")
                logger.warning(f"Attempt to register existing user with email: {ghp_user_email}.")
                form.add_error('email', "Looks like a user with that email already exists")
            else:
                instance.save()
                # ghp_user = get_object_or_404(GHPUser, email=ghp_user_email)
                logger.info(f"New GHPUser created and saved: {instance}. Attempting login.")
                print("Created ghp_user: ", instance)
                login(request, instance)
                logger.info(f"User {instance.username} logged in successfully after registration.")
                return HttpResponseRedirect(reverse('measure:ghp_user_account_view', args=(instance.id,)))
        else:
            logger.warning(f"CreateGHPUserForm is invalid. Errors: {form.errors}")
            print("Register form is not valid")
            print(form.errors)
            render(request, 'measure/register.html', {'form': form})
    else:
        #form = UserCreationForm()
        form = CreateGHPUserForm()
        logger.info("Rendering CreateGHPUserForm (GET request) for new user registration.")

    return render(request, 'measure/register.html', {'form': form})

@login_required(login_url='measure:login')
def base_view(request):
    logger.info(f"User {request.user.username} accessing base_view.")
    return render(request, 'measure/base.html', {})

@login_required(login_url='measure:login')
def user_view(request):
    logger.info(f"User {request.user.username} accessing user_view.")
    return render(request, 'measure/base_user.html', {})






@login_required(login_url='measure:login')
@permission_required(['measure.view_account', 'measure.view_ledger',
                      'measure.view_piece', 'measure.add_ledger'], raise_exception=True)
def refund_view(request, ghp_user_id, ghp_user_piece_id):
    logger.info(f"User {request.user.username} accessing refund_view for ghp_user_id: {ghp_user_id}, piece_id: {ghp_user_piece_id}. Request method: {request.method}")
    # get user, piece, and associated ledger entr(ies)
    ghp_refund_user = get_object_or_404(GHPUser, pk=ghp_user_id)
    piece = Piece.objects.filter(ghp_user=ghp_refund_user).filter(ghp_user_piece_id=ghp_user_piece_id).first()
    if not piece:
        logger.error(f"Piece not found in refund_view for ghp_user_id: {ghp_user_id}, piece_id: {ghp_user_piece_id}. User: {request.user.username}")
        return HttpResponse("Piece not found for refund", status=404)
     
    ledgers = Ledger.objects.filter(ghp_user=ghp_refund_user).filter(piece=piece).all()

    logger.debug(f"Refund view details: ghp_user: {ghp_refund_user}, piece: {piece}, ledgers: {ledgers}")
    print("Found ghp user: " + str(ghp_refund_user))
    print("Found piece: {} with pk: {}".format(str(piece), piece.pk))
    print("Found ledgers: " + str(ledgers))
    
    
    if request.method == 'POST':
        form = RefundPieceForm(request.POST, ghp_user=ghp_refund_user, piece=piece, ledgers=ledgers)
        if form.is_valid():
            logger.info(f"RefundPieceForm is valid for ghp_user: {ghp_refund_user.username}, piece_id: {ghp_user_piece_id} by user {request.user.username}.")

            instance = form.save(commit=False)
            # process the data in form.cleaned_data as required
            instance.save()
            logger.info(f"Refund processed and saved for ghp_user: {ghp_refund_user.username}, piece_id: {ghp_user_piece_id} by user {request.user.username}.")
            return HttpResponseRedirect(reverse('admin:measure_account_change', args=(ghp_user_id,)))
        else:
            logger.warning(f"RefundPieceForm is invalid for ghp_user: {ghp_refund_user.username}, piece_id: {ghp_user_piece_id} by user {request.user.username}. Errors: {form.errors}")
            print("Refund piece form is not valid")

            print(form.errors)
            return render(request, 'measure/refund_piece.html', {'form': form, 'ghp_user': ghp_refund_user, 'piece': piece, 'ledgers': ledgers})

    else:
        # GET request
        form = RefundPieceForm(ghp_user=ghp_refund_user, piece=piece, ledgers=ledgers)
        logger.info(f"Rendering RefundPieceForm (GET request) for ghp_user: {ghp_refund_user.username}, piece_id: {ghp_user_piece_id} by user {request.user.username}.")
    return render(request, 'measure/refund_piece.html', {'form': form, 'ghp_user': ghp_refund_user, 'piece': piece, 'ledgers': ledgers})

@login_required(login_url='measure:login')
@permission_required(['measure.view_account', 'measure.view_ledger',
                      'measure.view_piece', 'measure.add_ledger'], raise_exception=True)
def add_credit_view(request, ghp_user_id):
    logger.info(f"User {request.user.username} accessing add_credit_view for ghp_user_id: {ghp_user_id}. Request method: {request.method}")
    # get the user, and the user's account
    ghp_user = get_object_or_404(GHPUser, pk=ghp_user_id)
    ghp_user_account = get_object_or_404(Account, ghp_user=ghp_user)
    logger.debug(f"Add credit view details: ghp_user: {ghp_user}, account: {ghp_user_account}")
    print("Ghp user id: ", ghp_user_id)
    print("Found ghp user: " + str(ghp_user))
    print("Found account: " + str(ghp_user_account))
    if request.method == 'POST':
        form = AddCreditForm(request.POST, ghp_user=ghp_user, ghp_user_account=ghp_user_account)
        if form.is_valid():
            logger.info(f"AddCreditForm is valid for ghp_user: {ghp_user.username} by user {request.user.username}. Amount: {form.cleaned_data.get('amount')}")

            instance = form.save(commit=False)

            # process the data in form.cleaned_data as required
            instance.save()
            logger.info(f"Credit added and saved for ghp_user: {ghp_user.username} by user {request.user.username}.")
            return HttpResponseRedirect(reverse('admin:measure_account_change', args=(ghp_user_id,)))
        else:
            logger.warning(f"AddCreditForm is invalid for ghp_user: {ghp_user.username} by user {request.user.username}. Errors: {form.errors}")
            print("Add credit form is not valid")
            print(form.errors)
            return render(request, 'measure/add_credit.html', {'form': form, 'ghp_user': ghp_user, 'ghp_user_account': ghp_user_account})
    else:
        # GET request
        form = AddCreditForm(ghp_user=ghp_user, ghp_user_account=ghp_user_account)
        logger.info(f"Rendering AddCreditForm (GET request) for ghp_user: {ghp_user.username} by user {request.user.username}.")
    return render(request, 'measure/add_credit.html', {'form': form, 'ghp_user': ghp_user, 'ghp_user_account': ghp_user_account})

#@login_required(login_url='measure:login')
class HomePageView(TemplateView):
    template_name = 'measure/home.html'

    def get(self, request, *args, **kwargs):
        logger.info(f"User {request.user.username if request.user.is_authenticated else 'AnonymousUser'} accessing HomePageView.")
        return super().get(request, *args, **kwargs)

# new
#@login_required(login_url='measure:login')
@csrf_exempt
def stripe_config(request):
    logger.info("Stripe_config endpoint called.")
    if request.method == 'GET':
        stripe_config_data = {'publicKey': settings.STRIPE_PUBLISHABLE_KEY}
        logger.debug(f"Returning Stripe config data: {stripe_config_data}")
        return JsonResponse(stripe_config_data, safe=False)
    logger.warning(f"Stripe_config endpoint called with invalid method: {request.method}")
    return HttpResponse(status=405) # Method Not Allowed
    

@login_required(login_url='measure:login')
@csrf_exempt
def create_checkout_session(request):
    logger.info(f"User {request.user.username} attempting to create Stripe checkout session.")
    print("In Create checkout session view...")
    if request.method == 'GET':
        print("Request method is get")

        domain_url = settings.DOMAIN
        logger.debug(f"Domain URL for Stripe checkout: {domain_url}")
        print("Domain url: {}".format(domain_url))
        stripe.api_key = settings.STRIPE_SECRET_KEY
        print("Trying to get user and current location...")
        try:
            ghp_user_id = request.user.id
            ghp_user = get_object_or_404(GHPUser, pk=ghp_user_id)
            logger.debug(f"User for checkout: {ghp_user}")
            print("User: {}".format(ghp_user))
            current_location = ghp_user.get_location()
            ghp_user_name = ghp_user.first_name + ' ' + ghp_user.last_name
            ghp_user_email = ghp_user.email
            ghp_user_id_str = str(ghp_user.id) # Ensure ID is a string for metadata

            logger.debug(f"Current location for checkout: {current_location}")
            print("Current location: {}".format(current_location))
            print("Successfully got user and current location!")
        except Exception as e:
            logger.error(f"Error getting user or current location for Stripe checkout. User: {request.user.username if request.user.is_authenticated else 'Unknown User'}. Error: {e}", exc_info=True)
            print("Error getting user or current location: {}".format(e))
            current_location = 'Greenwich'
            ghp_user_name = 'Unknown User'
            ghp_user_email = 'Unknown Email'
            ghp_user_id_str = 'Unknown ID' # Ensure consistency

        # Prepare metadata dictionary
        # Ensure all values are strings as required by Stripe metadata
        checkout_metadata = {
            'user_location': str(current_location),
            'django_user_id': ghp_user_id_str,
            'ghp_user_name': str(ghp_user_name),
            'ghp_user_email': str(ghp_user_email),
        }
        print(f"Prepared Metadata: {checkout_metadata}")
        logger.info(f"Stripe checkout session metadata: {checkout_metadata}")

        print("Trying to create checkout session...")
        try:
            checkout_session = stripe.checkout.Session.create(
                client_reference_id=request.user.id if request.user.is_authenticated else None,
                success_url=domain_url + 'success?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=domain_url + 'cancelled/',
                mode='payment',
                line_items=[{
                    'price': 'price_1P37XFKNzblAdhbyy6uIvXj6',
                    'quantity': 5,
                    'adjustable_quantity': {
                        'enabled': True,
                        'minimum': 5,
                        'maximum': 250,
                    }
                }],
                # Metadata attached directly to the Session object
                metadata=checkout_metadata,

                # --- START CHANGE --- # TODO: This comment seems to be from original code
                # Pass metadata to the underlying Payment Intent
                payment_intent_data={
                    'metadata': checkout_metadata
                },
                # --- END CHANGE --- # TODO: This comment seems to be from original code
            )
            logger.info(f"Stripe checkout session created successfully for user {request.user.username}. Session ID: {checkout_session['id']}")
            print("Created checkout session")
            return JsonResponse({'sessionId': checkout_session['id']})
        except Exception as e:
            logger.error(f"Error creating Stripe checkout session for user {request.user.username}. Error: {e}", exc_info=True)
            print(f"Error creating checkout session: {e}")
            # Consider logging the full traceback here for better debugging
            import traceback
            traceback.print_exc()
            return JsonResponse({'error': str(e)}, status=500) # Return appropriate error status
    logger.warning(f"Create_checkout_session endpoint called with invalid method: {request.method} by user {request.user.username}")
    return HttpResponse(status=405) # Method Not Allowed

#@login_required(login_url='measure:login')
class StripeSuccessView(TemplateView):
    template_name = 'measure/stripe_success.html'

    def get(self, request, *args, **kwargs):
        logger.info(f"User {request.user.username if request.user.is_authenticated else 'AnonymousUser'} landed on StripeSuccessView. Session ID: {request.GET.get('session_id')}")
        return super().get(request, *args, **kwargs)
    
#@login_required(login_url='measure:login')
class StripeCancelledView(TemplateView):
    template_name = 'measure/stripe_cancelled.html'

    def get(self, request, *args, **kwargs):
        logger.info(f"User {request.user.username if request.user.is_authenticated else 'AnonymousUser'} landed on StripeCancelledView.")
        return super().get(request, *args, **kwargs)

#@login_required(login_url='measure:login')
@csrf_exempt
def stripe_webhook(request):
    logger.info("Stripe webhook received.")
    print("In stripe webhook view...")
    stripe.api_key = settings.STRIPE_SECRET_KEY
    endpoint_secret = settings.STRIPE_ENDPOINT_SECRET
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = None
    print("Received webhook")
    try:
        print("Trying to construct event")
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
        logger.info(f"Stripe webhook event constructed successfully. Event ID: {event.id}, Type: {event.type}")
        print("Constructed event")
    except ValueError as e:
        # Invalid payload
        logger.error(f"Invalid Stripe webhook payload. Error: {e}", exc_info=True)
        print("Error constructing event: ", e)
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        logger.error(f"Invalid Stripe webhook signature. Error: {e}", exc_info=True)
        print("Error verifying signature: ", e)
        return HttpResponse(status=400)

    logger.info(f"Processing Stripe event type: {event['type']}")
    print("Event type: {}".format(event['type']))
    # Handle the checkout.session.completed event
    if event['type'] == 'checkout.session.completed':
        logger.info(f"Processing checkout.session.completed event. Session ID: {event['data']['object']['id']}")
        print("Event type is checkout.session.completed")
        print("Event: {}".format(event))
        print("Event type: {}".format(event['type']))
        print("Event data: {}".format(event['data']))
        print("Event object: {}".format(event['data']['object']))

        session = event['data']['object']
        print("Payment was successful.")
        # This method will be called when user successfully purchases something.
        print("Calling handle_checkout_session")
        response = handle_checkout_session(session)
        
        # Return success response to Stripe first
        if response.status_code == 200:
            logger.info(f"handle_checkout_session successful for session ID: {session.get('id')}. Preparing redirect if applicable.")
            # If successful, trigger redirect but still return 200 to Stripe
            client_reference_id = session.get("client_reference_id")
            if client_reference_id:
                redirect_url = reverse('measure:ghp_user_account_view', args=(client_reference_id,))
                response['HX-Redirect'] = redirect_url
            return response
        else:
            logger.error(f"handle_checkout_session failed for session ID: {session.get('id')}. Status: {response.status_code}, Content: {response.content}")
            # If there was an error, return the error response
            return response
    else:
        logger.info(f"Received unhandled Stripe event type: {event['type']}")

    return HttpResponse(status=200)

#@login_required(login_url='measure:login')
def handle_checkout_session(session):
    session_id = session.get("id")
    logger.info(f"Handling checkout session. Session ID: {session_id}")
    # client_reference_id = user's id
    print("session: {}".format(session))
    client_reference_id = session.get("client_reference_id")
    payment_intent = session.get("payment_intent")
    print("Client reference id: {}".format(client_reference_id))
    print("Payment intent: {}".format(payment_intent))
    ghp_user = None
    if client_reference_id is None:
        logger.warning(f"Client_reference_id is None for Stripe session ID: {session_id}. Attempting to find user by email.")
        print("WARNING: Client wasn't logged in when purchasing!")
        # Customer wasn't logged in when purchasing
        print("Trying to match customer by email")
        email = session.get("customer_details").get("email")
        if email is None:
            email = session.get("customer_email")
        print("Email: {}".format(email))
        if email is not None:
            try: 
                ghp_user = GHPUser.objects.get(email=session.get("customer_email"))
                logger.info(f"Found GHPUser by email: {email} for Stripe session ID: {session_id}. User: {ghp_user.username}")
            except GHPUser.DoesNotExist:
                logger.error(f"Could not find GHPUser by email: {email} for Stripe session ID: {session_id}. Payment not processed by website.", extra={'stripe_session': session})
                print("WARNING: Could not find customer by email")
                print("ERROR: STRIPE PAYMENT WAS NOT PROCESSED BY WEBSITE.")
                print(session)
                print("Canceling attempt to add credit to user account.")
                print("ERROR: STAFF WILL HAVE TO MANUALLY ADD CREDIT TO USER ACCOUNT.")
                return HttpResponse(status=400,
                                    content="Could not find customer by account or email! Stripe payment was not processed by website!")
    # Customer was logged in we can now fetch the Django user and make changes to our models
    try:
        ghp_user = GHPUser.objects.get(pk=client_reference_id)#get_object_or_404(GHPUser, pk=client_reference_id)
        logger.info(f"Processing payment for GHPUser: {ghp_user.username} (ID: {client_reference_id}) from Stripe session ID: {session_id}.")
        print(ghp_user.username, "just purchased something.")
        #ghp_user = GHPUser.objects.get(username=user.username)
        ghp_user_transaction_number = Ledger.objects.filter(ghp_user=ghp_user).count() + 1
        print("GHP user: {}".format(ghp_user))
        print("GHP user transaction number: {}".format(ghp_user_transaction_number))
        amount = decimal.Decimal(float(session.get("amount_subtotal")) / 100.0 )# cents to dollars to decimal
        print("Amount: {}".format(amount))
        try:
            # Check if this is a duplicate transaction 2/10/24
            print("Checking if this is a duplicate transaction")
            print("Session id: ", session_id)
            print("Payment intent: ", payment_intent)
            print("GHP user: ", ghp_user)
            print("Amount: ", amount)
            # Get all transactions with the same stripe_session_id. Check the note text to see if
            if session_id is not None:
                ledgers = Ledger.objects.filter(stripe_session_id=session_id).all()
                print("Ledgers: ", ledgers)
                if ledgers.count() > 0:
                    logger.warning(f"Duplicate transaction detected for Stripe session ID: {session_id}, GHPUser: {ghp_user.username}. Transaction already processed.")
                    print("Duplicate transaction detected")
                    print("Already processed this transaction.")
                    print("Canceling attempt to add credit to user account.")
                    #print("ERROR: STAFF WILL HAVE TO MANUALLY ADD CREDIT TO USER ACCOUNT.")
                    return HttpResponse(status=200) # return OK for this so Stripe will not try to resend the webhook

        except Exception as e:
            logger.error(f"Error checking for duplicate transaction for Stripe session ID: {session_id}, GHPUser: {ghp_user.username}. Error: {e}", exc_info=True)
            print("Error checking for duplicate transaction: ", e)
            return HttpResponse(status=400,
                                content="Error when checking for duplicate transaction. This does not indicate a duplicate transaction.")

        try:
            logger.info(f"Creating ledger entry for GHPUser: {ghp_user.username}, Amount: {amount}, Stripe Session ID: {session_id}.")
            print("Creating ledger entry")
            print("ghp_user: ", ghp_user)
            print("amount: ", amount)
            print("Session id: ", session_id)
            print("transaction_type: ", 'auto_user_add_firing_credit')
            print("note: ", 'Stripe Payment of ${}'.format(amount))
            user_payment = Ledger.objects.create(
                                ghp_user=ghp_user,
                                amount= amount, # amount is postive because the user is buying credit
                                transaction_type='auto_user_add_firing_credit',
                                note='Stripe Payment of ${}'.format(amount),
                                stripe_session_id=session_id,
            )
            print("Saving ledger entry")
            user_payment.save()
            logger.info(f"Ledger entry created successfully for GHPUser: {ghp_user.username}. Ledger ID: {user_payment.transaction_id}")
            print("Finished creating ledger entry")
            return HttpResponse(status=200)
        except Exception as e:
            logger.error(f"Error creating ledger entry for GHPUser: {ghp_user.username}, Stripe Session ID: {session_id}. Error: {e}", exc_info=True)
            print("Error creating ledger entry: ", e)
            return HttpResponse(status=400,
                                content="Error creating a ledger entry for this transaction.")

        # TODO: make changes to our models.

    except GHPUser.DoesNotExist:
        logger.error(f"GHPUser does not exist for client_reference_id: {client_reference_id} from Stripe session ID: {session_id}. Payment not processed.", extra={'stripe_session': session})
        print("Webhook error: GHPUser does not exist")
        return HttpResponse(status=400,
                            content="Could not find customer by account or email! Stripe payment was not processed by website!")
    except Exception as e:
        logger.critical(f"Unexpected error in handle_checkout_session for Stripe session ID: {session_id}. Client Reference ID: {client_reference_id}. Error: {e}", exc_info=True, extra={'stripe_session': session})
        print("Error: ", e)
        return HttpResponse(status=400,
                            content="Error processing Stripe payment.")

def job_to_printer_text(job):
    # Process the job and return the text to be printed
    logger.debug(f"Generating printer text for job ID: {job.get('id')}, type: {job.get('receipt_type')}")
    if job['receipt_type'] == 'Bisque':
        print_string = """
BISQUE FIRING SLIP
DO NOT THROW AWAY

PLACE THIS SLIP WITH 

YOUR PIECE & CLASS CHIP

ON BISQUE FIRING SHELF

Name: {}

Date: {}

LxWxH: {} x {} x {}

Handles: {}

Course Number: {}

Bisque Temp: {}

Piece #: {}


""".format(job['ghp_user_name'], job['piece_date'], job['length'], job['width'], job['height'], job['handles'], job['course_number'], job['bisque_temp'], job['piece_number'])

    elif job['receipt_type'] == 'Glaze':
        print_string = """
GLAZE FIRING SLIP

DO NOT THROW AWAY

SAVE THIS SLIP FOR

GLAZE FIRING DROP OFF

Name: {}

Date: {}

LxWxH: {} x {} x {}

Handles: {}

Course Number: {}

Glaze Temp: {}

Piece #: {}


    """.format(job['ghp_user_name'], job['piece_date'], job['length'], job['width'], job['height'], job['handles'], job['course_number'], job['glaze_temp'], job['piece_number'])
    else:
        logger.warning(f"Unknown receipt type: {job.get('receipt_type')} for job ID: {job.get('id')}")
        return {'id': job.get('id'), 'print_string': "ERROR: Unknown receipt type"}

    return {'id': job['id'], 'print_string': print_string}


@csrf_exempt
def get_print_jobs_chelsea(request):
    logger.info(f"get_print_jobs_chelsea called. Method: {request.method}")
    if request.method == 'GET':
        try:
            print_server_key = request.GET.get('secret_key', '')
            logger.debug(f"GET request for print jobs. Provided key (first 5 chars): {print_server_key[:5]}")

            print_server_secret_key = settings.PRINT_SERVER_SECRET_KEY
            greenwich_print_server_secret_key = settings.GREENWICH_PRINT_SERVER_SECRET_KEY

            if not print_server_secret_key:
                logger.error("PRINT_SERVER_SECRET_KEY is not set in settings.")
                return JsonResponse({'error': 'Chelsea print server secret key not configured'}, status=500)
            if not greenwich_print_server_secret_key:
                logger.error("GREENWICH_PRINT_SERVER_SECRET_KEY is not set in settings.")
                return JsonResponse({'error': 'Greenwich print server secret key not configured'}, status=500)

            data = {'unprinted_receipts': None}
            location_processed = None

            if print_server_key == print_server_secret_key:
                location_processed = "Chelsea"
                logger.info("Valid secret key for Chelsea print server.")
                unprinted_receipts_qs = PieceReceipt.objects.filter(printed=False, piece_location='Chelsea').all()
            elif print_server_key == greenwich_print_server_secret_key:
                location_processed = "Greenwich"
                logger.info("Valid secret key for Greenwich print server.")
                unprinted_receipts_qs = PieceReceipt.objects.filter(printed=False, piece_location='Greenwich').all()
            else:
                logger.warning(f"Invalid secret key provided for get_print_jobs. Key (first 5 chars): {print_server_key[:5]}")
                return JsonResponse({'error': 'Invalid secret key'}, status=403)

            if location_processed and unprinted_receipts_qs.exists():
                logger.info(f"{unprinted_receipts_qs.count()} unprinted receipts found for {location_processed}.")
                # Convert queryset to list of dicts for job_to_printer_text and modification
                unprinted_receipts_list = list(unprinted_receipts_qs.values('id', 'receipt_type', 'ghp_user_name', 'piece_date', 'length', 'width', 'height', 'handles', 'course_number', 'bisque_temp', 'glaze_temp', 'piece_number'))
                data['unprinted_receipts'] = [job_to_printer_text(job) for job in unprinted_receipts_list]

                # Mark receipts as printed
                receipt_ids_to_mark = [r['id'] for r in unprinted_receipts_list]
                PieceReceipt.objects.filter(id__in=receipt_ids_to_mark).update(printed=True)
                logger.info(f"Marked {len(receipt_ids_to_mark)} receipts as printed for {location_processed}.")
            elif location_processed:
                logger.info(f"No unprinted receipts found for {location_processed}.")
            
            return JsonResponse(data)

        except Exception as e:
            logger.error(f"Error in GET get_print_jobs_chelsea: {e}", exc_info=True)
            return JsonResponse({'error': 'An unexpected error occurred'}, status=500)

    elif request.method == 'POST':
        try:
            print_server_key = request.POST.get('secret_key', '')
            logger.debug(f"POST request to mark receipts printed. Provided key (first 5 chars): {print_server_key[:5]}")

            print_server_secret_key = settings.PRINT_SERVER_SECRET_KEY
            greenwich_print_server_secret_key = settings.GREENWICH_PRINT_SERVER_SECRET_KEY
            
            valid_key_used = False
            location_processed = None

            if not print_server_secret_key:
                logger.error("PRINT_SERVER_SECRET_KEY is not set in settings for POST.")
                # Fall through to invalid key check, or return early if preferred
            if not greenwich_print_server_secret_key:
                logger.error("GREENWICH_PRINT_SERVER_SECRET_KEY is not set in settings for POST.")
                 # Fall through to invalid key check, or return early if preferred

            if print_server_key == print_server_secret_key:
                valid_key_used = True
                location_processed = "Chelsea"
                logger.info("Valid secret key for Chelsea (POST to mark printed).")
            elif print_server_key == greenwich_print_server_secret_key:
                valid_key_used = True
                location_processed = "Greenwich"
                logger.info("Valid secret key for Greenwich (POST to mark printed).")
            
            if valid_key_used:
                receipt_ids_str = request.POST.get('receipt_ids', '')
                if not receipt_ids_str:
                    logger.warning(f"No receipt_ids provided in POST request for {location_processed}.")
                    return JsonResponse({'error': 'receipt_ids are required'}, status=400)
                
                # Assuming receipt_ids is a comma-separated string e.g., "1,2,3"
                try:
                    receipt_ids = [int(rid.strip()) for rid in receipt_ids_str.split(',') if rid.strip()]
                except ValueError:
                    logger.error(f"Invalid receipt_ids format: {receipt_ids_str} for {location_processed}. Must be comma-separated integers.")
                    return JsonResponse({'error': 'Invalid receipt_ids format. Must be comma-separated integers.'}, status=400)

                if not receipt_ids:
                    logger.warning(f"Empty list of receipt_ids after parsing: {receipt_ids_str} for {location_processed}.")
                    return JsonResponse({'error': 'No valid receipt_ids provided'}, status=400)

                logger.info(f"Attempting to mark {len(receipt_ids)} receipts as printed for {location_processed}: {receipt_ids}")
                updated_count = PieceReceipt.objects.filter(id__in=receipt_ids, piece_location=location_processed).update(printed=True)
                logger.info(f"Successfully marked {updated_count} receipts as printed for {location_processed}.")
                return HttpResponse(status=200)
            else:
                logger.warning(f"Invalid secret key provided for POST get_print_jobs. Key (first 5 chars): {print_server_key[:5]}")
                return JsonResponse({'error': 'Invalid secret key'}, status=403)
        
        except Exception as e:
            logger.error(f"Error in POST get_print_jobs_chelsea: {e}", exc_info=True)
            return JsonResponse({'error': 'An unexpected error occurred'}, status=500)
        
    else:
        logger.warning(f"Unsupported method {request.method} for get_print_jobs_chelsea.")
        return HttpResponse(status=405) # Method Not Allowed

