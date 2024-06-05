from django.urls import path, include, reverse_lazy
from django.contrib.auth import views as auth_views
from django.contrib import admin

# urlpatterns = [
# ]
from . import views

app_name = 'measure'
urlpatterns = [
    path("admin/", admin.site.urls),
 
    ##path('', views.index_view, name='index'),
    path('', views.user_view, name='user'),
    path('base/', views.base_view, name='base'),

    path('user/', views.user_view, name='user'),
    path('register/', views.register_page, name='register'),
    path('login/', auth_views.LoginView.as_view(next_page='measure:user'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='measure:login'), name='logout'),
    # path('login/password_reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset.html', 
    #                                                                    email_template_name='registration/password_reset_email_edit.html',
    #                                                                    success_url = reverse_lazy("measure:password_reset_done")), 
    #                                                                    name='login_password_reset'),


    path('password_reset/', auth_views.PasswordResetView.as_view(success_url = reverse_lazy("measure:password_reset_done"),
                                                                 ##template_name='password_reset/password_reset_form.html',
                                                                email_template_name='emails/password_reset_email.html',
                                                                 ), name='password_reset'),
    
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name = 'password_reset/password_reset_done.html'
                                                                          ), name='password_reset_done'),
    
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(success_url = reverse_lazy("measure:password_reset_complete"),
                                                                               ## template_name = "password_reset/password_reset_confirm.html",
                                                                                ), name='password_reset_confirm'),
    
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name = "password_reset/password_reset_complete.html"), 
                                                                        name='password_reset_complete'),
    # path(
    #     "admin/password_reset/",
    #     auth_views.PasswordResetView.as_view(),
    #     name="admin_password_reset",
    #     ),
    # path(
    #     "admin/password_reset/done/",
    #     auth_views.PasswordResetDoneView.as_view(),
    #     name="password_reset_done",
    # ),
    # path(
    #     "reset/<uidb64>/<token>/",
    #     auth_views.PasswordResetConfirmView.as_view(),
    #     name="password_reset_confirm",
    # ),
    # path(
    #     "reset/done/",
    #     auth_views.PasswordResetCompleteView.as_view(),
    #     name="password_reset_complete",
    # ),

    # the 'name' value as called by the {% url %} template tag
    # to change the url, modifiy the path() argument here
    path('<int:ghp_user_id>/', views.ghp_user_piece_view, name='ghp_user_piece_view'), #as_view()
    path('<int:ghp_user_id>/account/', views.ghp_user_account_view, name='ghp_user_account_view'), #as_view()
    path('<int:ghp_user_id>/location/', views.ModifyLocationView, name='modify_location'), #as_view()

    #path('<int:pk>/email/', views.email, name='email'),
    path('<int:ghp_user_id>/piece/', views.PieceView, name='piece'),
    path('<int:ghp_user_id>/piece/<int:ghp_user_piece_id>/', views.ModifyPieceView, name='modify_piece'),
    path('<int:ghp_user_id>/piece/<int:ghp_user_piece_id>/refund/', views.refund_view, name='refund_piece'),
    path('<int:ghp_user_id>/account/credit/', views.add_credit_view, name='add_credit'),
    ##path('home/', views.HomePageView.as_view(), name='home'),
    path('stripe_config/', views.stripe_config, name='stripe_config'),
    path('create-checkout-session/', views.create_checkout_session), # new
    path('success/', views.StripeSuccessView.as_view()), # new
    path('cancelled/', views.StripeCancelledView.as_view()), # new
    path('webhook/', views.stripe_webhook), # new

    path('api/printjobs/', views.get_print_jobs_chelsea, name='get_print_jobs_chelsea'),





]


