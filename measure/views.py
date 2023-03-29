from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic
from .forms import PieceForm
from .models import GHPUser, Account, Course, Location, Term, CourseInstance, Piece, Ledger
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

def generate_ghp_users(num_customers=100, p_student=0.9, p_teacher=0.2, p_staff=0.1, p_admin=0.03):
    with open('first_names.csv', 'r') as f:
      first_names = list(csv.reader(f))[0]
    with open('last_names.csv', 'r') as f:
      last_names = list(csv.reader(f))[0]
    
    phone_numbers = np.random.randint(1000000000, 9999999999, num_customers).astype(str)
    emails = [first_names[i] + '_' + last_names[i] + '@gmail.com' for i in range(num_customers)]

    dobs = list(datetime.date.today() - datetime.timedelta(days=np.random.randint(0, 365*100, num_customers)) for i in range(num_customers))

    students = np.zeros(num_customers) + np.random.choice([0,1], size=num_customers, p=[1-p_student, p_student]) 
    teachers = np.zeros(num_customers) + np.random.choice([0,1], size=num_customers, p=[1-p_teacher, p_teacher])
    staff = np.zeros(num_customers) + np.random.choice([0,1], size=num_customers, p=[1-p_staff, p_staff])
    admin = np.zeros(num_customers) + np.random.choice([0,1], size=num_customers, p=[1-p_admin, p_admin])
    
    if np.sum(teachers) == 0:
        teachers[0] = 1
    if np.sum(staff) == 0:
        staff[1] = 1
    if np.sum(admin) == 0:
        admin[2] = 1
    
    for i in range(num_customers):
      ghp_user = GHPUser(
        first_name = first_names[i],
        last_name = last_names[i],
        phone_number = phone_numbers[i],
        email = emails[i],
        dob = dobs[i],
        current_student = students[i],
        current_teacher = teachers[i],
        current_staff = staff[i],
        current_admin = admin[i]
      )
      ghp_user.save()
    
    # while GHPUser.objects.filter(ghp_username=ghp_username).exists():
    #   ghp_username += '1'

    # cust = RrskCustomers(
    #   ghp_user = GHPUser.objects.create_ghp_user(ghp_username=ghp_username, email=email, password='VERYVERYHARDPASSWORD1234'),
    #   cust_phone_no = 9999999999 - i,
    #   cust_type = cust_type,
    #   cust_country = 'USA',
    #   cust_state = states[idx],
    #   cust_city = cities[idx],
    #   cust_street = '{} street'.format(i),
    #   cust_no = '{}'.format(i),
    #   cust_zip = 10000 + i,
    #   cust_fname = cust_fname,
    #   cust_lname = cust_lname)
    # cust.save()