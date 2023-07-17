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
# Create your views here.



# def email_check(user):
#     return user.email.endswith("@example.com")


# @user_passes_test(email_check)

@login_required(login_url='measure:login')
def index_view(request):
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
    if not request.user.get_username() == ghp_user.get_username():
        # if the user is not the correct user, redirect to the login page
        print("Requesting user: {}, does not have access to ghp_user: {}".format(request.user.get_username(), ghp_user.get_username()))
        return redirect(reverse("measure:login"))#/?next=%s" % request.path))

    ghp_user_piece_list = Piece.objects.filter(ghp_user_id=ghp_user_id).order_by('-ghp_user_piece_id').all()
    return render(request, 'measure/ghp_user_pieces.html', {'ghp_user': ghp_user, 'ghp_user_piece_list': ghp_user_piece_list})

@login_required(login_url='measure:login')
def ghp_user_account_view(request, ghp_user_id):
    ghp_user = get_object_or_404(GHPUser, pk=ghp_user_id)
    print("Checking if user has permission to view account page")
    if not request.user.get_username() == ghp_user.get_username():
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
    if not request.user.get_username() == ghp_user.get_username():
        # if the user is not the correct user, redirect to the login page
        print("Requesting user: {}, does not have access to ghp_user: {}".format(request.user.get_username(), ghp_user.get_username()))
        return redirect(reverse("measure:login/?next=%s" % request.path))

    if request.method == 'POST':
        form = PieceForm(request.POST, ghp_user=ghp_user)
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
        form = PieceForm(ghp_user=ghp_user)
    return render(request, 'measure/piece.html', {'form': form})


@login_required(login_url='measure:login')
def ModifyPieceView(request, ghp_user_id, ghp_user_piece_id):
    ghp_user = get_object_or_404(GHPUser, pk=ghp_user_id)
    print("Checking if user has permission to view modify piece page")
    if not request.user.get_username() == ghp_user.get_username():
        # if the user is not the correct user, redirect to the login page
        print("Requesting user: {}, does not have access to ghp_user: {}".format(request.user.get_username(), ghp_user.get_username()))
        return redirect(reverse("measure:login_view/?next=%s" % request.path))

    piece = Piece.objects.filter(ghp_user=ghp_user).filter(ghp_user_piece_id=ghp_user_piece_id).first()
    print("Found user: " + str(ghp_user))
    print("Found piece: {} with pk: {}".format(str(piece), piece.pk))
    if request.method == 'POST':
        form = ModifyPieceForm(request.POST, ghp_user=ghp_user, piece=piece)
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

    print("Found user: " + str(ghp_refund_user))
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
def add_credit_view(request, ghp_user_id):
    # get the user, and the user's account
    ghp_user = get_object_or_404(GHPUser, pk=ghp_user_id)
    ghp_user_account = get_object_or_404(Account, ghp_user=ghp_user)
    print("Found user: " + str(ghp_user))
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