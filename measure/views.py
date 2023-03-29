from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic
from .forms import PieceForm
from .models import GHPUser, Account, Course, Location, Term, CourseInstance, Piece, Ledger
from django.contrib.auth.models import User
import csv
import numpy as np
import datetime
# Create your views here.

class IndexView(generic.ListView):
    template_name = 'measure/index.html'
    context_object_name = 'ghp_user_list'

    def get_queryset(self):
        """Return the list of all ghp_users."""
        return GHPUser.objects.order_by('last_name').all()

class GHPUserView(generic.DetailView):
    model = GHPUser
    template_name = 'measure/ghp_user.html'


#class PieceView(generic.FormView):
def Piece(request, ghp_user_id):
    ghp_user = get_object_or_404(GHPUser, pk=ghp_user_id)

    if request.method == 'POST':
        form = PieceForm(request.POST, ghp_user=ghp_user)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.save()
            # process the data in form.cleaned_data as required
            return HttpResponseRedirect(reverse('measure:ghp_user', args=(ghp_user_id,)))
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

