from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic
from django.utils import timezone
from .forms import PieceForm, CreateGHPUserForm, ModifyPieceForm, RefundPieceForm, AddCreditForm
from .models import GHPUser, Account, Piece, Ledger
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

    ghp_user_admins = GHPUser.objects.filter(current_admin=True).order_by('last_name').all()
    ghp_user_staff = GHPUser.objects.filter(current_staff=True).order_by('last_name').all()
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


def base_view(request):
    return render(request, 'measure/base.html', {})

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
@login_required(login_url='measure:login')
@csrf_exempt
def stripe_config(request):
    if request.method == 'GET':
        stripe_config = {'publicKey': settings.STRIPE_PUBLISHABLE_KEY}
        return JsonResponse(stripe_config, safe=False)
    

@login_required(login_url='measure:login')
@csrf_exempt
def create_checkout_session(request):
    if request.method == 'GET':
        #TODO: need to change the following line to the correct domain
        domain_url = 'https://ghp-measurement-d2e329f35d3b.herokuapp.com/'
        stripe.api_key = settings.STRIPE_SECRET_KEY
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
                    'price': 'price_1NykHQE1Tl2FOfocAeJNrJKN',
                    'quantity': 1,
                },
            ],
            )
            return JsonResponse({'sessionId': checkout_session['id']})
        except Exception as e:
            return JsonResponse({'error': str(e)})

#@login_required(login_url='measure:login')
class StripeSuccessView(TemplateView):
    template_name = 'measure/stripe_success.html'

#@login_required(login_url='measure:login')
class StripeCancelledView(TemplateView):
    template_name = 'measure/stripe_cancelled.html'

@login_required(login_url='measure:login')
@csrf_exempt
def stripe_webhook(request):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    endpoint_secret = settings.STRIPE_ENDPOINT_SECRET
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = None
    print("Received webhook")
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return HttpResponse(status=400)

    # Handle the checkout.session.completed event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        print("Payment was successful.")
        # This method will be called when user successfully purchases something.
        handle_checkout_session(session)
        return HttpResponseRedirect(reverse('measure:ghp_user_account_view', args=(session.get("client_reference_id"),)))

    return HttpResponse(status=200)

@login_required(login_url='measure:login')
def handle_checkout_session(session):
    print("Handling checkout session")
    # client_reference_id = user's id
    print("session: {}".format(session))
    client_reference_id = session.get("client_reference_id")
    payment_intent = session.get("payment_intent")
    print("Client reference id: {}".format(client_reference_id))
    print("Payment intent: {}".format(payment_intent))
    if client_reference_id is None:
        # Customer wasn't logged in when purchasing
        return

    # Customer was logged in we can now fetch the Django user and make changes to our models
    try:
        user = User.objects.get(id=client_reference_id)
        print(user.username, "just purchased something.")
        ghp_user = GHPUser.objects.get(username=user.username)
        ghp_user_transaction_number = Ledger.objects.filter(ghp_user=ghp_user).count() + 1
        print("GHP user: {}".format(ghp_user))
        print("GHP user transaction number: {}".format(ghp_user_transaction_number))
        amount = float(session.get("amount_subtotal")) / 100.0 # cents to dollars
        print("Amount: {}".format(amount))
        try:
            Ledger.objects.create(
                date = timezone.now(),
                ghp_user=ghp_user,
                ghp_user_transaction_number=ghp_user_transaction_number,
                amount= amount, # amount is negative because this is a fee
                transaction_type='auto_user_add_firing_credit',
                note='Stripe Payment of ${}'.format(amount),
                piece=None
                )
            print("Created ledger entry")
        except:
            print("Error creating ledger entry")
            pass
        # TODO: make changes to our models.

    except User.DoesNotExist:
        print("Webhook error: User does not exist")
        pass




import tablib
from import_export import resources

def ImportGHPUserView(request):
    print("in view")
    if request.method == 'POST':
        print("Request method is post")
        model_resource = resources.modelresource_factory(model=GHPUser)() # to take the model as a reference
        new_users = request.FILES['csv_events'] # to get the file
        # this part is to add the a column with the user id
        dataset = tablib.Dataset(
            headers=['first_name', 'last_name', 'email', 'current_location', 'balance']
        ).load(new_users.read().decode('utf-8'), format='csv')
        
        
        emails = dataset['email']
        balances = dataset['balance']
        locations = dataset['current_location']
        dataset = dataset.subset(
            cols=[0,1,2]
        )

        # dataset.append_col(
        #     col=tuple(f'{user_id}' for _ in range(dataset.height)),
        #     header='user_id'
        # )


        result = model_resource.import_data(dataset, dry_run=True)  # Test the data import

        if not result.has_errors():
            model_resource.import_data(dataset, dry_run=False)  # Actually import now
    print("redirecting")
    return redirect(reverse('measure:base'))


def ImportGHPUserViewBase(request):
    print("in import base")
    #if request.method == 'POST':
        #print("Request method is post")
    return render(request, 'measure/import_ghp_user.html')


from tablib import Dataset
from .admin import GHPUserResource
def simple_upload(request):
    if request.method == 'POST':
        print("defining ghp user resource")
        ghp_user_resource = GHPUserResource()
        dataset = tablib.Dataset(
            ##headers=['first_name', 'last_name', 'email', 'location', 'balance']
        )
        print("Getting file")
        new_users = request.FILES['user_import_file']

        print("reading file...")

        ## CANNOT HAVE SPACES BETWEEN HEADERS OR DATA ENTRIES OR IT WILL NOT WORK.
        imported_data = dataset.load(new_users.read().decode('utf-8'), format='csv')
        print("imported data: ", imported_data)
        print("datset: ", dataset)
        print("Dataset dict: ", dataset.dict)
        #print("pulling emails and balances")
        print("trying to look at dataset columns")
        try:
            print(dataset['first_name'])
        except Exception as e:
            print("Error getting first_name: ", e)
        
        print("trying to look at other columns")

        try:
            print("Trying to look at dataset email")
            print(dataset['email'])
        except Exception as e:
            print("Error getting emails: ", e)
            print("Trying to look at dataset username")
            print(dataset['username'])
        try:
            emails = dataset['email']
        except Exception as e:
            print("Error getting emails: ", e)
            emails = dataset['username']

        print("emails: ", emails)
        
        balances = dataset['balance']
        print("balances: ", balances)

        locations = dataset['location']
        print("locations: ", locations)

        print("dropping balance column")
        del dataset['balance']
        print("appending username column")
        dataset.append_col(dataset['email'], header='username')
        #dataset['username'] = dataset['email']
        print("Dry running import")
        result = ghp_user_resource.import_data(dataset, dry_run=True)  # Test the data import
        print("Result: ", result)
        if not result.has_errors():
            print("Dry run was successful. Importing data.")
            ghp_user_resource.import_data(dataset, dry_run=False)  # Actually import now
            print("Import was successful")
            print("Setting user balances")
            for email, balance in zip(emails, balances):
                print("email: {}, balance: {}".format(email, balance))
                ghp_user = GHPUser.objects.get(email=email)
                print("ghp_user: ", ghp_user)
                ghp_user.account.balance = balance
                ghp_user.account.save()
                print("ghp_user.account.balance: ", ghp_user.account.balance)
        else:
            print("Dry run was not successful")
            print(result)
    return render(request, 'measure/import_ghp_user.html')