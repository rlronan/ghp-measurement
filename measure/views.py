from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic
from django.utils import timezone
from .forms import PieceForm, CreateGHPUserForm, ModifyPieceForm, RefundPieceForm, AddCreditForm
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


# @user_passes_test(email_check)

@login_required(login_url='measure:login')
def index_view(request):
    print("Checking if user has permission to account index page")
    if not user_is_staff_check(request.user):
        print("Requesting user: {}, does not have access to the account index page".format(request.user.get_username()))
        return redirect(reverse("measure:login"))#/?next=%s" % request.path))

    ghp_user_admins = GHPUser.objects.filter(current_faculty=True).order_by('last_name').all()
    ghp_user_staff = GHPUser.objects.filter(current_ghp_staff=True).order_by('last_name').all()
    ghp_user_students = GHPUser.objects.filter(current_student=True).order_by('last_name').all()
    num_rows = max([ghp_user_admins.count(), ghp_user_staff.count(), ghp_user_students.count()])

    num_rows = list(range(num_rows))
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
        return Piece.objects.filter(ghp_user_id=self.ghp_user_id).order_by('-date').all()

@login_required(login_url='measure:login')
def ghp_user_piece_view(request, ghp_user_id):
    ghp_user = get_object_or_404(GHPUser, pk=ghp_user_id)
    print("Checking if user has permission to view piece overview page")
    if not (user_owns_object_check(request.user, ghp_user) 
            or user_is_staff_check(request.user)):
#    if not request.user.get_username() == ghp_user.get_username():
        # if the user is not the correct user, redirect to the login page
        print("Requesting user: {}, does not have access to ghp_user: {}".format(request.user.get_username(), ghp_user.get_username()))
        return redirect(reverse("measure:login"))#/?next=%s" % request.path))

    ghp_user_piece_list = Piece.objects.filter(ghp_user_id=ghp_user_id).order_by('-ghp_user_piece_id').all()
    return render(request, 'measure/ghp_user_pieces.html', {'ghp_user': ghp_user, 'ghp_user_piece_list': ghp_user_piece_list})

@login_required(login_url='measure:login')
def ghp_user_account_view(request, ghp_user_id):
    ghp_user = get_object_or_404(GHPUser, pk=ghp_user_id)
    print("Checking if user has permission to view account page")
    if not (user_owns_object_check(request.user, ghp_user) 
            or user_is_staff_check(request.user)):
    #if not request.user.get_username() == ghp_user.get_username():
        # if the user is not the correct user, redirect to the login page
        print("Requesting user: {}, does not have access to ghp_user: {}".format(request.user.get_username(), ghp_user.get_username()))
        return redirect(reverse("measure:login/?next=%s" % request.path))

    ghp_user_account = ghp_user.account #Account.objects.filter(ghp_user=ghp_user).first() # should only be one
    ghp_user_transactions = Ledger.objects.filter(ghp_user=ghp_user).order_by('-ghp_user_transaction_number').all()

    return render(request, 'measure/ghp_user_account.html', {
        'ghp_user': ghp_user,
        'ghp_user_account': ghp_user_account,
        'ghp_user_transactions': ghp_user_transactions,
        
    })


@login_required(login_url='measure:login')
def PieceView(request, ghp_user_id):
    ghp_user = get_object_or_404(GHPUser, pk=ghp_user_id)
    print("Checking if user has permission to view piece page")
    if not (user_owns_object_check(request.user, ghp_user) 
            or user_is_staff_check(request.user)):
        # if the user is not the correct user, redirect to the login page
        print("Requesting user: {}, does not have access to ghp_user: {}".format(request.user.get_username(), ghp_user.get_username()))
        return redirect(reverse("measure:login/?next=%s" % request.path))
    
    user_balance = ghp_user.account.balance #Account.objects.filter(ghp_user=ghp_user).first() # should only be one
    if request.method == 'POST':
        form = PieceForm(request.POST, request.FILES, ghp_user=ghp_user, user_balance=user_balance)
        if form.is_valid():
            print("Measuring piece form is valid")
            instance = form.save(commit=False)
            
            instance.save()
            # process the data in form.cleaned_data as required
            return HttpResponseRedirect(reverse('measure:ghp_user_piece_view', args=(ghp_user_id,)))
        else:
            print("Measuring piece form is not valid")
            print(form.errors)
            return render(request, 'measure/piece.html', {'form': form})

    else:
        form = PieceForm(ghp_user=ghp_user, user_balance=user_balance)
    return render(request, 'measure/piece.html', {'form': form})


@login_required(login_url='measure:login')
def ModifyPieceView(request, ghp_user_id, ghp_user_piece_id):
    ghp_user = get_object_or_404(GHPUser, pk=ghp_user_id)
    print("Checking if user has permission to view modify piece page")
    if not (user_owns_object_check(request.user, ghp_user) 
            or user_is_staff_check(request.user)):
        # if the user is not the correct user, redirect to the login page
        print("Requesting user: {}, does not have access to ghp_user: {}".format(request.user.get_username(), ghp_user.get_username()))
        return redirect(reverse("measure:login_view/?next=%s" % request.path))

    piece = Piece.objects.filter(ghp_user=ghp_user).filter(ghp_user_piece_id=ghp_user_piece_id).first()
    piece_image = piece.image
    print("Found user: " + str(ghp_user))
    print("Found piece: {} with pk: {}".format(str(piece), piece.pk))
    if request.method == 'POST':
        form = ModifyPieceForm(request.POST, request.FILES, ghp_user=ghp_user, piece=piece)# piece_image=piece_image)
        if form.is_valid():
            form.instance.pk = piece.id
            form.instance.date = piece.date
            instance = form.save(commit=False)
            # process the data in form.cleaned_data as required
            instance.save()
            return HttpResponseRedirect(reverse('measure:ghp_user_piece_view', args=(ghp_user_id,)))
        else:
            print("Modify piece form is not valid")
            print(form.errors)
            return render(request, 'measure/modify_piece.html', {'form': form, 'ghp_user': ghp_user, 'piece': piece})

    else:
        form = ModifyPieceForm(ghp_user=ghp_user, piece=piece)
    return render(request, 'measure/modify_piece.html', {'form': form})



#@unauthenticated_user
def register_page(request):
    if request.method == 'POST':
        form = CreateGHPUserForm(request.POST)
        if form.is_valid():
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
                form.add_error('email', "Looks like a user with that email already exists")
            else:
                instance.save()
                # ghp_user = get_object_or_404(GHPUser, email=ghp_user_email)
                
                print("Created ghp_user: ", instance)
                login(request, instance)
                
                return HttpResponseRedirect(reverse('measure:ghp_user_account_view', args=(instance.id,)))
        else:
            print("Register form is not valid")
            print(form.errors)
            render(request, 'measure/register.html', {'form': form})
    else:
        #form = UserCreationForm()
        form = CreateGHPUserForm()

    return render(request, 'measure/register.html', {'form': form})

@login_required(login_url='measure:login')
def base_view(request):
    return render(request, 'measure/base.html', {})

@login_required(login_url='measure:login')
def user_view(request):
    return render(request, 'measure/base_user.html', {})






@login_required(login_url='measure:login')
@permission_required(['measure.view_account', 'measure.view_ledger',
                      'measure.view_piece', 'measure.add_ledger'], raise_exception=True)
def refund_view(request, ghp_user_id, ghp_user_piece_id):
    # get user, piece, and associated ledger entr(ies)
    ghp_refund_user = get_object_or_404(GHPUser, pk=ghp_user_id)
    piece = Piece.objects.filter(ghp_user=ghp_refund_user).filter(ghp_user_piece_id=ghp_user_piece_id).first()
     
    ledgers = Ledger.objects.filter(ghp_user=ghp_refund_user).filter(piece=piece).all()

    print("Found ghp user: " + str(ghp_refund_user))
    print("Found piece: {} with pk: {}".format(str(piece), piece.pk))
    print("Found ledgers: " + str(ledgers))
    
    
    if request.method == 'POST':
        form = RefundPieceForm(request.POST, ghp_user=ghp_refund_user, piece=piece, ledgers=ledgers)
        if form.is_valid():

            instance = form.save(commit=False)
            # process the data in form.cleaned_data as required
            instance.save()
            return HttpResponseRedirect(reverse('admin:measure_account_change', args=(ghp_user_id,)))
        else:
            print("Refund piece form is not valid")

            print(form.errors)
            return render(request, 'measure/refund_piece.html', {'form': form, 'ghp_user': ghp_refund_user, 'piece': piece, 'ledgers': ledgers})

    else:
        # GET request
        form = RefundPieceForm(ghp_user=ghp_refund_user, piece=piece, ledgers=ledgers)
    return render(request, 'measure/refund_piece.html', {'form': form, 'ghp_user': ghp_refund_user, 'piece': piece, 'ledgers': ledgers})

@login_required(login_url='measure:login')
@permission_required(['measure.view_account', 'measure.view_ledger',
                      'measure.view_piece', 'measure.add_ledger'], raise_exception=True)
def add_credit_view(request, ghp_user_id):
    # get the user, and the user's account
    ghp_user = get_object_or_404(GHPUser, pk=ghp_user_id)
    ghp_user_account = get_object_or_404(Account, ghp_user=ghp_user)
    print("Ghp user id: ", ghp_user_id)
    print("Found ghp user: " + str(ghp_user))
    print("Found account: " + str(ghp_user_account))
    if request.method == 'POST':
        form = AddCreditForm(request.POST, ghp_user=ghp_user, ghp_user_account=ghp_user_account)
        if form.is_valid():

            instance = form.save(commit=False)

            # process the data in form.cleaned_data as required
            instance.save()
            return HttpResponseRedirect(reverse('admin:measure_account_change', args=(ghp_user_id,)))
        else:
            print("Add credit form is not valid")
            print(form.errors)
            return render(request, 'measure/add_credit.html', {'form': form, 'ghp_user': ghp_user, 'ghp_user_account': ghp_user_account})
    else:
        # GET request
        form = AddCreditForm(ghp_user=ghp_user, ghp_user_account=ghp_user_account)
    return render(request, 'measure/add_credit.html', {'form': form, 'ghp_user': ghp_user, 'ghp_user_account': ghp_user_account})

#@login_required(login_url='measure:login')
class HomePageView(TemplateView):
    template_name = 'measure/home.html'
# new
#@login_required(login_url='measure:login')
@csrf_exempt
def stripe_config(request):
    if request.method == 'GET':
        stripe_config = {'publicKey': settings.STRIPE_PUBLISHABLE_KEY}
        return JsonResponse(stripe_config, safe=False)
    

@login_required(login_url='measure:login')
@csrf_exempt
def create_checkout_session(request):
    print("In Create checkout session view...")
    if request.method == 'GET':
        print("Request method is get")
        #TODO: need to change the following line to the correct domain
        domain_url = settings.DOMAIN ##'http://localhost:8000/'#'https://ghp-measurement-d2e329f35d3b.herokuapp.com/'
        print("Domain url: {}".format(domain_url))
        stripe.api_key = settings.STRIPE_SECRET_KEY
        print("Trying to create checkout session...")
        try:
            # Create new Checkout Session for the order
            # Other optional params include:
            # [billing_address_collection] - to display billing address details on the page
            # [customer] - if you have an existing Stripe Customer ID
            # [payment_intent_data] - capture the payment later
            # [customer_email] - prefill the email input in the form
            # For full details see https://stripe.com/docs/api/checkout/sessions/create

            # ?session_id={CHECKOUT_SESSION_ID} means the redirect will have the session ID set as a query param
            checkout_session = stripe.checkout.Session.create(
                client_reference_id=request.user.id if request.user.is_authenticated else None,
                success_url=domain_url + 'success?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=domain_url + 'cancelled/',
                #payment_method_types=['card'],
                mode='payment',
                            line_items=[
                {
                    # Provide the exact Price ID (for example, pr_1234) of the product you want to sell
                    'price': 'price_1OmmODKNzblAdhbySMe4YoN7', # moving price to production 'price_1OiMoHKNzblAdhbyq93B7xrG', # moving price to ghp_account 'price_1NykHQE1Tl2FOfocAeJNrJKN',
                    'quantity': 1,
                },
            ],
            )
            print("Created checkout session")
            return JsonResponse({'sessionId': checkout_session['id']})
        except Exception as e:
            print("Error creating checkout session")
            return JsonResponse({'error': str(e)})

#@login_required(login_url='measure:login')
class StripeSuccessView(TemplateView):
    template_name = 'measure/stripe_success.html'
    
#@login_required(login_url='measure:login')
class StripeCancelledView(TemplateView):
    template_name = 'measure/stripe_cancelled.html'

#@login_required(login_url='measure:login')
@csrf_exempt
def stripe_webhook(request):
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
        print("Constructed event")
    except ValueError as e:
        # Invalid payload
        print("Error constructing event: ", e)
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        print("Error verifying signature: ", e)
        return HttpResponse(status=400)

    print("Event type: {}".format(event['type']))
    # Handle the checkout.session.completed event
    if event['type'] == 'checkout.session.completed':
        print("Event type is checkout.session.completed")
        print("Event: {}".format(event))
        print("Event type: {}".format(event['type']))
        print("Event data: {}".format(event['data']))
        print("Event object: {}".format(event['data']['object']))

        session = event['data']['object']
        print("Payment was successful.")
        # This method will be called when user successfully purchases something.
        print("Calling handle_checkout_session")
        handle_checkout_session(session)
        print("Handled checkout session. Redirecting to user account page")
        return HttpResponseRedirect(reverse('measure:ghp_user_account_view', args=(session.get("client_reference_id"),)))

    return HttpResponse(status=200)

#@login_required(login_url='measure:login')
def handle_checkout_session(session):
    print("Handling checkout session")
    # client_reference_id = user's id
    print("session: {}".format(session))
    session_id = session.get("id")
    client_reference_id = session.get("client_reference_id")
    payment_intent = session.get("payment_intent")
    print("Client reference id: {}".format(client_reference_id))
    print("Payment intent: {}".format(payment_intent))
    ghp_user = None
    if client_reference_id is None:
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
            except GHPUser.DoesNotExist:
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
                    print("Duplicate transaction detected")
                    print("Already processed this transaction.")
                    print("Canceling attempt to add credit to user account.")
                    #print("ERROR: STAFF WILL HAVE TO MANUALLY ADD CREDIT TO USER ACCOUNT.")
                    return HttpResponse(status=200) # return OK for this so Stripe will not try to resend the webhook

        except Exception as e:
            print("Error checking for duplicate transaction: ", e)
            return HttpResponse(status=400,
                                content="Error when checking for duplicate transaction. This does not indicate a duplicate transaction.")

        try:
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
            print("Finished creating ledger entry")
            return HttpResponse(status=200)
        except Exception as e:
            print("Error creating ledger entry: ", e)
            return HttpResponse(status=400,
                                content="Error creating a ledger entry for this transaction.")

        # TODO: make changes to our models.

    except GHPUser.DoesNotExist:
        print("Webhook error: GHPUser does not exist")
        return HttpResponse(status=400,
                            content="Could not find customer by account or email! Stripe payment was not processed by website!")
    except Exception as e:
        print("Error: ", e)
        return HttpResponse(status=400,
                            content="Error processing Stripe payment.")



@csrf_exempt
def get_print_jobs(request):
    if request.method == 'GET':
        print("In get print jobs view GET")
        print_server_key = request.GET.get('secret_key', '')
        print("Provided secret key: ", print_server_key)
        print_server_secret_key = settings.PRINT_SERVER_SECRET_KEY
        if print_server_secret_key == '':
            print("Print server secret key not set")
            #raise ValueError("PRINT_SERVER_SECRET_KEY is not set")
            return JsonResponse({'error': 'Print server secret key not set'}, status=500)
        elif print_server_key == print_server_secret_key:  # Replace 'YOUR_SECRET_KEY' with your actual secret key
            print("Valid secret key, getting unprinted receipts")
            all_receipts = PieceReceipt.objects.all()
            #print("All receipts: ", all_receipts)
            unprinted_receipts = PieceReceipt.objects.filter(printed=False).filter(piece_location='Chelsea').all()
            print("Unprinted Receipts: ", unprinted_receipts)
            data = {
                'unprinted_receipts': list(unprinted_receipts.values())
            }
            # Mark the receipts as printed since we are sending to the printer, and I cannot get the local server to respond..
            for receipt_obj in unprinted_receipts:
                print("Marking receipt as printed")
                receipt = get_object_or_404(PieceReceipt, pk=receipt_obj.id)
                receipt.printed = True
                receipt.save()

            return JsonResponse(data)   
        else:
            print("Invalid secret key")
            return JsonResponse({'error': 'Invalid secret key'}, status=403)
    elif request.method == 'POST':
        print("In get print jobs view POST")

        print_server_key = request.POST.get('secret_key', '')
        print("Provided secret key: ", print_server_key)
        print_server_secret_key = settings.PRINT_SERVER_SECRET_KEY
        if print_server_secret_key == '':
            print("Print server secret key not set")
            #raise ValueError("PRINT_SERVER_SECRET_KEY is not set")
            return JsonResponse({'error': 'Print server secret key not set'}, status=500)
        elif print_server_key == print_server_secret_key:
            print("Valid secret key, marking receipt as printed")
            receipt_ids = request.POST.get('receipt_ids', '')
            print("Receipt ids: ", receipt_ids)
            for receipt_id in receipt_ids:
                receipt = get_object_or_404(PieceReceipt, pk=receipt_id)
                receipt.printed = True
                receipt.save()
            return HttpResponse(status=200)
        
    else:
        print("Cannot understand request")
        return HttpResponse(status=400)

