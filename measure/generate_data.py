import numpy as np
import decimal
import datetime
import csv
import math
from django.utils import timezone
from .models import GHPUser, Account, Piece, Ledger
from .constants import GLAZE_TEMPS,  BISQUE_TEMPS, USER_FIRING_SCALE, FACULTY_FIRING_SCALE, USER_GLAZING_SCALE, FACULTY_GLAZING_SCALE, MINIMUM_PRICE, TRANSACTION_TYPES

# Create your tests here.
def generate_ghp_user(num_customers=100, p_student=0.9, p_staff=0.1, p_admin=0.03):
    """ Generate a list of GHPUsers with random names, phone numbers, and emails.
    
    NOTE THIS FUNCTION MODIFIES THE DATABASE. DO NOT RUN THIS FUNCTION ON A PRODUCTION DATABASE.
    """

    with open('first_names.csv', 'r') as f:
      first_names = list(csv.reader(f))[0]
    with open('last_names.csv', 'r') as f:
      last_names = list(csv.reader(f))[0]
    
    phone_numbers = np.random.randint(0, 20000, num_customers).astype(str)
    #emails = [first_names[i] + '_' + last_names[i] + '@gmail.com' for i in range(num_customers)]

    #dobs = list(datetime.date.today() - datetime.timedelta(days=np.random.randint(0, 365*100)) for i in range(num_customers))

    students = np.zeros(num_customers) + np.random.choice([0,1], size=num_customers, p=[1-p_student, p_student]) 
    #teachers = np.zeros(num_customers) + np.random.choice([0,1], size=num_customers, p=[1-p_teacher, p_teacher])
    staff = np.zeros(num_customers) + np.random.choice([0,1], size=num_customers, p=[1-p_staff, p_staff])
    admin = np.zeros(num_customers) + np.random.choice([0,1], size=num_customers, p=[1-p_admin, p_admin])
    consent = np.zeros(num_customers) + np.random.choice([0,1], size=num_customers)
    consent = consent.astype('bool')
    consent_date = np.where(consent, timezone.now() - datetime.timedelta(days=np.random.randint(0, 365)), None)
    
    #if np.sum(teachers) == 0:
    #    teachers[0] = 1
    if np.sum(staff) == 0:
        staff[1] = 1
    if np.sum(admin) == 0:
        admin[2] = 1
    
    for i in range(num_customers):
        first_name = first_names[np.random.randint(0, len(first_names))]
        last_name = last_names[np.random.randint(0, len(first_names))]
        try:
            print("attempting to create GHPuser: " + first_name + " " + last_name + " ...")
            ghp_user = GHPUser.objects.create(
                username = first_name + '_' + last_name + '@gmail.com',
                password = 'VeryComplexPassword123!',
                #password2 = 'VeryComplexPassword123!', 
                first_name = first_name,
                last_name = last_name,
                phone_number = phone_numbers[i],
                email = first_name + '_' + last_name + '@gmail.com',
                #dob = dobs[i],
                current_student = students[i],
                #current_teacher = teachers[i],
                current_ghp_staff = staff[i],
                current_faculty = admin[i],
                
                consent = consent[i],
                consent_date = consent_date[i],
            )
        except Exception as e:
            print("exception: ")
            print(e)
            continue


def generate_balances():

    ghp_users = GHPUser.objects.all().order_by('?')
    for ghp_user in ghp_users:
        Ledger.objects.create(
            date = timezone.now(),
            ghp_user=ghp_user,
            ghp_user_transaction_number=1,
            amount= np.random.randint(0, 300),
            transaction_type='manual_gh_add_misc_credit',
            note='Setting user balances to random values for testing purposes.',
            piece=None
        )


def generate_piece(num_pieces=1000):
    """ Generate a pieces for andom users."""

    for i in range(num_pieces):
        ghp_user = GHPUser.objects.all().order_by('?')[i % GHPUser.objects.count()]
        ghp_user_piece_id = 0 # placeholder
        date = timezone.now() - datetime.timedelta(days=np.random.randint(0, 365*10))
        length = decimal.Decimal(np.random.uniform(0.5, 21.0))
        width = decimal.Decimal(np.random.uniform(0.5, 21.0))
        height = decimal.Decimal(np.random.uniform(3.0, 22.0))

        # round length width and height up to the nearest 0.5
        length = decimal.Decimal(math.ceil(length * 2) / 2).quantize(decimal.Decimal('0.1'))
        width = decimal.Decimal(math.ceil(width * 2) / 2).quantize(decimal.Decimal('0.1'))
        height = decimal.Decimal(math.ceil(height * 2) / 2).quantize(decimal.Decimal('0.1'))

        size = decimal.Decimal(length * width * height).quantize(decimal.Decimal('0.01'))

        GLAZE_TEMP_INTERNAL = list(i[0] for i in GLAZE_TEMPS)
        glaze_temp = np.random.choice(GLAZE_TEMP_INTERNAL)

        BISQUE_TEMP_INTERNAL = list(i[0] for i in BISQUE_TEMPS)
        bisque_temp = np.random.choice(BISQUE_TEMP_INTERNAL, p=[0.95, 0.05])

        glaze_temp = np.where(bisque_temp == "None", GLAZE_TEMP_INTERNAL[0], glaze_temp) # if bisque_temp is None, glaze_temp must not be None
        # get price scaling factor based on whether the user is current_ghp_staff or current_faculty or not
        if ghp_user.current_ghp_staff or ghp_user.current_faculty:
            if bisque_temp != "None":
                firing_price = size * decimal.Decimal(0.01)
            else:
                firing_price = size * decimal.Decimal(0.00)
            price = firing_price

            if glaze_temp != "None":
                glaze_price = size * decimal.Decimal(0.01)
            else:
                glaze_price = size * decimal.Decimal(0.00)
            price += glaze_price
        else:
            if bisque_temp != "None":
                firing_price = size * decimal.Decimal(0.01)
            else:
                firing_price = size * decimal.Decimal(0.00)
            price = firing_price
            if glaze_temp != "None":
                glaze_price = size * decimal.Decimal(0.01)
            else:
                glaze_price = size * decimal.Decimal(0.00)
            price += glaze_price

        
        course_number = np.random.choice(['W', 'G', 'H']) + str(np.random.randint(1, 20))

        bisque_fired = np.random.choice([True, False], p=[0.3, 0.7])
        if bisque_fired and glaze_temp != "None":
            glaze_fired = np.random.choice([True, False], p=[0.1, 0.9])
        else:
            glaze_fired = False
        piece_description = np.random.choice(['Bowl', 'Vase', 'Cup', 'Mug', 'Lamp', 'Sculpture', 'Plate'])
        if glaze_temp != "None":
            glaze_description = np.random.choice(['Blue', 'Green', 'Red', 'Yellow', 'Orange', 'Purple', 'White', 'Black'])
            glaze_description += ' ' + np.random.choice(['Gloss', 'Matte', 'Satin', 'Shiny', 'Sparkly', 'Glowing', 'Frosted', ''])
            if np.random.random() < 0.2:
                glaze_description += np.random.choice(['Blue', 'Green', 'Red', 'Yellow', 'Orange', 'Purple', 'White', 'Black'])
                glaze_description += ' ' + np.random.choice(['Gloss', 'Matte', 'Satin', 'Shiny', 'Sparkly', 'Glowing', 'Frosted', ''])
        else:
            glaze_description = ''
        
        if glaze_description == '':
            note = piece_description
        else:
            note = piece_description + ' with ' + glaze_description + ' glaze'
        # image

        piece = Piece.objects.create(
            ghp_user = ghp_user,
            ghp_user_piece_id = ghp_user_piece_id,
            date=date,
            length = length,
            width = width,
            height = height,
            size = size,
            glaze_temp = glaze_temp,
            bisque_temp = bisque_temp,
            firing_price = firing_price,
            glazing_price = glaze_price,
            price = price,
            course_number=course_number,
            bisque_fired = bisque_fired,
            glaze_fired = glaze_fired,
            piece_description = piece_description,
            glaze_description = glaze_description,
            note = note,
        )


def generate_all():
    """ Generate all the data for the database.
    
    NOTE THIS FUNCTION MODIFIES THE DATABASE. DO NOT RUN THIS FUNCTION ON A PRODUCTION DATABASE.
    """
    generate_ghp_user()
    generate_balances()
    # generate_course()
    # generate_location()
    # generate_term()
    # generate_course_instance()
    generate_piece()