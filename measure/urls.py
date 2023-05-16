from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.contrib import admin

# urlpatterns = [
# ]
from . import views

app_name = 'measure'
urlpatterns = [
    path("admin/", admin.site.urls),

    path('', views.index_view, name='index'),
    path('base/', views.base_view, name='base'),
    path('register/', views.register_page, name='register'),
    path('login/', auth_views.LoginView.as_view(next_page='measure:base'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    # path('accounts/login', views.login, name='login'),
    # path('measure/accounts/login', views.login, name='login'),
    

    # the 'name' value as called by the {% url %} template tag
    # to change the url, modifiy the path() argument here
    path('<int:ghp_user_id>/', views.ghp_user_piece_view, name='ghp_user_piece_view'), #as_view()
    path('<int:ghp_user_id>/account/', views.ghp_user_account_view, name='ghp_user_account_view'), #as_view()
    #path('<int:pk>/email/', views.email, name='email'),
    path('<int:ghp_user_id>/piece/', views.PieceView, name='piece'),
    path('<int:ghp_user_id>/piece/<int:ghp_user_piece_id>/', views.ModifyPieceView, name='modify_piece'),

    path("accounts/", include("django.contrib.auth.urls")),

    path(
        "admin/password_reset/",
        auth_views.PasswordResetView.as_view(),
        name="admin_password_reset",
        ),
    path(
        "admin/password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
]


