# DEFINTE SITE-WIDE CONSTANTS FOR THE MEASURE APP HERE

# Glaze Temperature Options
# The first value is the value that is stored in the database
# The second value is the value that is displayed to the user
GLAZE_TEMPS  = [
        ("10",   "Δ 10 (Cone 10)"),
        ("6",    "Δ 6 (Cone 6)"),
        ("2",    "Δ 2 (Cone 2)"),
        ("014",  "Δ 014 (Cone 014)"),
        ("06G",   "Δ 06 (Cone 06)"),
        ("04",   "Δ 04 (Cone 04)"),
        ("None", "None"),
]

BISQUE_TEMPS = [
        ("06B",   "Δ 06 BISQUE (Cone 06 Bisque)"),
        ("None", "None"),

]

# Price Scaling
USER_FIRING_SCALE = 0.03
STAFF_FIRING_SCALE = 0.01

USER_GLAZING_SCALE = 0.03
STAFF_GLAZING_SCALE = 0.01

MINIMUM_PRICE = 1.00


# Transaction Types

TRANSACTION_TYPES = [
    
        ('auto_bisque_fee', 'AUTO: Bisque Firing Fee'), 
        ('auto_glaze_fee', 'AUTO: Glaze Firing Fee'), 
        ('auto_refund_bisque_fee', 'AUTO: Refund Bisque Firing Fee'),
        ('auto_refund_glaze_fee', 'AUTO: Refund Glaze Firing Fee'),
        ('auto_user_add_firing_credit', 'AUTO: User Add Firing Credit'),
        ('auto_gh_add_firing_credit', 'AUTO: GH Add Firing Credit'),
        ('auto_gh_add_misc_credit', 'AUTO: GH Add Misc Credit'),
        ('auto_gh_add_misc_charge', 'AUTO: GH Add Misc Charge'),
        ('manual_gh_add_misc_credit', 'MANUAL: GH Add Misc Credit'),
        ('manual_gh_add_misc_charge', 'MANUAL: GH Add Misc Charge'),
]