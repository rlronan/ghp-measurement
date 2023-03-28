from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic
from .forms import PieceForm
from .models import User, Account, Course, Location, Term, CourseInstance, Piece, Ledger
# Create your views here.

class IndexView(generic.ListView):
    template_name = 'measure/index.html'
    context_object_name = 'user_list'

    def get_queryset(self):
        """Return the list of all users."""
        return User.objects.order_by('last_name').all()

class UserView(generic.DetailView):
    model = User
    template_name = 'measure/user.html'


#class PieceView(generic.FormView):
def Piece(request, user_id):
    user = get_object_or_404(User, pk=user_id)

    if request.method == 'POST':
        form = PieceForm(request.POST, user=user)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.save()
            # process the data in form.cleaned_data as required
            return HttpResponseRedirect(reverse('measure:user', args=(user_id,)))
    else:
        form = PieceForm(user=user)
    return render(request, 'measure/piece.html', {'form': form})



# def index(request):
#     user_list = User.objects.order_by('last_name').all()
#     context = {'user_list' : user_list}
#     return render(request, 'measure/index.html', context)



# def user(request, user_id):
#     user = get_object_or_404(User, pk=user_id)
#     return render(request, 'measure/user.html', {'user' : user})

