from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic
from .forms import PieceForm
from .models import GHPUser, Account, Piece, Ledger #Course, Location, Term, CourseInstance,
from django.contrib.auth.models import User
import csv
import numpy as np
import datetime
# Create your views here.

# def index_view(request):
#     ghp_user_list = GHPUser.objects.order_by('last_name').all()
#     return render(request, 'measure/index.html', {'ghp_user_list': ghp_user_list})

def index_view(request):
    #ghp_user_list = GHPUser.objects.order_by('last_name').all()
    ghp_user_admins = GHPUser.objects.filter(current_admin=True).order_by('last_name').all()
    ghp_user_staff = GHPUser.objects.filter(current_staff=True).order_by('last_name').all()
    # ghp_user_teachers = GHPUser.objects.filter(current_teacher=True).order_by('last_name').all()
    ghp_user_students = GHPUser.objects.filter(current_student=True).order_by('last_name').all()
    num_rows = max([ghp_user_admins.count(), ghp_user_staff.count(), ghp_user_students.count()])

    # Cannot iterate over a range in a template so replace num_rows with a list of the same length
    num_rows = list(range(num_rows))
    return render(request, 'measure/index.html', {
        'num_rows': num_rows,
        'ghp_user_admins': ghp_user_admins,
        'ghp_user_staff': ghp_user_staff,
        # 'ghp_user_teachers': ghp_user_teachers,
        'ghp_user_students': ghp_user_students,})

# class GHPUserView(generic.DetailView):
#     model = GHPUser
#     template_name = 'measure/ghp_user.html'
#     context_object_name = 'ghp_user_piece_list'

#     def get_queryset(self):
#         """Return the list of all pieces associated with a ghp_user."""
#         return Piece.objects.filter(ghp_user_id=self.ghp_user_id).order_by('date').all()

def ghp_user_piece_view(request, ghp_user_id):
    ghp_user = get_object_or_404(GHPUser, pk=ghp_user_id)
    ghp_user_piece_list = Piece.objects.filter(ghp_user_id=ghp_user_id).order_by('ghp_user_piece_id').all()
    return render(request, 'measure/ghp_user_pieces.html', {'ghp_user': ghp_user, 'ghp_user_piece_list': ghp_user_piece_list})


def ghp_user_account_view(request, ghp_user_id):
    ghp_user = get_object_or_404(GHPUser, pk=ghp_user_id)
    ghp_user_account = ghp_user.account #Account.objects.filter(ghp_user=ghp_user).first() # should only be one
    ghp_user_transactions = Ledger.objects.filter(ghp_user=ghp_user).order_by('ghp_user_transaction_number').all()

    return render(request, 'measure/ghp_user_account.html', {
        'ghp_user': ghp_user,
        'ghp_user_account': ghp_user_account,
        'ghp_user_transactions': ghp_user_transactions,
        
    })


#class PieceView(generic.FormView):
def PieceView(request, ghp_user_id):
    ghp_user = get_object_or_404(GHPUser, pk=ghp_user_id)

    if request.method == 'POST':
        form = PieceForm(request.POST, ghp_user=ghp_user)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.save()
            # process the data in form.cleaned_data as required
            return HttpResponseRedirect(reverse('measure:ghp_user_piece_view', args=(ghp_user_id,)))
    else:
        form = PieceForm(ghp_user=ghp_user)
    return render(request, 'measure/piece.html', {'form': form})



# def index(request):
#     ghp_user_list = GHPUser.objects.order_by('last_name').all()
#     context = {'ghp_user_list' : ghp_user_list}
#     return render(request, 'measure/index.html', context)



# def ghp_user(request, ghp_user_id):
#     ghp_user = get_object_or_404(GHPUser, pk=ghp_user_id)
#     return render(request, 'measure/ghp_user.html', {'ghp_user' : ghp_user})

