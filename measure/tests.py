from django.test import TestCase
import numpy as np
import decimal
import datetime
import csv
from django.utils import timezone
from .models import GHPUser, Account, Course, Location, Term, CourseInstance, Piece, Ledger


# Create your tests here.
def generate_ghp_users(num_customers=100, p_student=0.9, p_teacher=0.2, p_staff=0.1, p_admin=0.03):
    """ Generate a list of GHPUsers with random names, phone numbers, and emails.
    
    NOTE THIS FUNCTION MODIFIES THE DATABASE. DO NOT RUN THIS FUNCTION ON A PRODUCTION DATABASE.
    """

    with open('first_names.csv', 'r') as f:
      first_names = list(csv.reader(f))[0]
    with open('last_names.csv', 'r') as f:
      last_names = list(csv.reader(f))[0]
    
    phone_numbers = np.random.randint(0, 20000, num_customers).astype(str)
    emails = [first_names[i] + '_' + last_names[i] + '@gmail.com' for i in range(num_customers)]

    dobs = list(datetime.date.today() - datetime.timedelta(days=np.random.randint(0, 365*100)) for i in range(num_customers))

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


def generate_course(num_courses=10):
    """ Generate a list of Courses with random names and codes.
    
    NOTE THIS FUNCTION MODIFIES THE DATABASE. DO NOT RUN THIS FUNCTION ON A PRODUCTION DATABASE.
    """
    course_names = ['INT./ADV. Handbuilding', 'Beginner Wheel', 'Intermediate Wheel', 'Advanced Wheel', 'Intermediate Handbuilding', 'Advanced Handbuilding', 'Glaze', 'Ceramics History', 'ADV. Ceramics History', 'Real Ceramics History']
    course_codes = ['H5', 'W7', 'W1', 'W10', 'H2', 'H3', 'G4', 'C5', 'C6', 'C1']
    for i in range(num_courses):
      course = Course(
        name = course_names[i],
        code = course_codes[i]
      )
      course.save()

def generate_location(num_locations=10):
    """ Generate a list of Locations with random room names and addresses.
    
    NOTE THIS FUNCTION MODIFIES THE DATABASE. DO NOT RUN THIS FUNCTION ON A PRODUCTION DATABASE.
    """
    room_names = ['2nd Floor Wheel', '301', '2nd Floor Handbuilding', '2nd Floor Glaze', '252']
    addresses = ['123 Main St.', '456 Main St.', '789 Main St.']
    for i in range(num_locations):
        room = room_names[i % len(room_names)]
        address = addresses[i % len(addresses)]
        type = 'Wheel' if 'Wheel' in room else 'Handbuilding' if 'Handbuilding' in room else 'Glaze' if 'Glaze' in room else 'Other'

        location = Location(
            room = room,
            address = address,
            type = type
        )
        location.save()

def generate_term(num_terms=20):
    """ Generate a list of Terms with random names and dates.
    
    NOTE THIS FUNCTION MODIFIES THE DATABASE. DO NOT RUN THIS FUNCTION ON A PRODUCTION DATABASE.
    """
    term_names = ['Spring', 'Summer', 'Fall', 'Spring-6-Week', 'Summer-6-Week', 'Fall-6-Week']
    for i in range(num_terms):
        term_name = term_names[i % len(term_names)]
        start_date = datetime.date.today() - datetime.timedelta(days=np.random.randint(0, 365*10))
        end_date = start_date + datetime.timedelta(days=7*8 if '6-Week' in term_name else 7*10)
        term = Term(
            name = term_name + ' ' + str(start_date.year),
            start_date = start_date,
            end_date = end_date
        )
        term.save()


def generate_course_instance(num_course_instances=50):
    """ Generate a list of CourseInstances with random names and dates.
    """
    for i in range(num_course_instances):
        course = Course.objects.all()[i % Course.objects.count()]
        term = Term.objects.all()[i % Term.objects.count()]
        if course.code[:1] == 'H':
            location = Location.objects.filter(type__exact='Handbuilding')[
                i % Location.objects.filter(type__exact='Handbuilding').count()
                ]
        elif course.code[:1] == 'W':
            location = Location.objects.filter(
                type__exact='Wheel'
            )[i % Location.objects.filter(
                type__exact='Wheel'
            ).count()]
        elif course.code[:1] == 'G':
            location = Location.objects.filter(
                type__exact='Glaze'
            )[i % Location.objects.filter(
                type__exact='Glaze'
            ).count()]
        else:
            location = Location.objects.all()[i % Location.objects.count()]
        

        teachers = GHPUser.objects.all()[i % GHPUser.objects.count()]
        students = GHPUser.objects.all().order_by('?')[:np.random.randint(1, 10) + 1]
        weekday = np.random.choice(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'])
        start_time = (timezone.now() - datetime.timedelta(hours=np.random.randint(0, 24)))
        end_time = start_time + datetime.timedelta(hours=np.random.randint(1, 4))
        course_instance = CourseInstance(
            name = course.name + ' ' + term.name,
            term = term,
            course = course,
            location = location,
            type = location.type,
            weekday = weekday,
            start_time = start_time.time(),
            end_time = end_time.time()
        )
        course_instance.save()
        if type(teachers) == GHPUser:
            course_instance.teachers.add(teachers)
        else:
            for teacher in teachers:
                course_instance.teachers.add(teacher)
        if type(students) == GHPUser:
            course_instance.students.add(students)
        else:
            for student in students:
                course_instance.students.add(student)


def generate_piece(num_pieces=1000):
    """ Generate a pieces for andom users."""

    for i in range(num_pieces):
        ghp_user = GHPUser.objects.all().order_by('?')[i % GHPUser.objects.count()]
        ghp_user_piece_id = 0 # placeholder
        length = decimal.Decimal(np.random.uniform(0.1, 10.0))
        width = decimal.Decimal(np.random.uniform(0.1, 10.0))
        height = decimal.Decimal(np.random.uniform(1.5, 20.0))
        size = decimal.Decimal(length * width * height)
        price = size * decimal.Decimal(0.06)
        bisque_fired = np.random.choice([True, False], p=[0.3, 0.7])
        if bisque_fired:
            glaze_fired = np.random.choice([True, False], p=[0.1, 0.9])
        else:
            glaze_fired = False
        damaged = np.random.choice([True, False], p=[0.01, 0.99])
# TODO: FIX THIS SO IT FILTERS BY STUDENTS
        #course = CourseInstance.objects.filter(students__contains=ghp_user).order_by('?')[0]
        course = CourseInstance.objects.all().order_by('?')[0]
        piece = Piece(
            ghp_user = ghp_user,
            ghp_user_piece_id = ghp_user_piece_id,
            length = length,
            width = width,
            height = height,
            size = size,
            price = price,
            bisque_fired = bisque_fired,
            glaze_fired = glaze_fired,
            damaged = damaged
        )
        piece.save()


