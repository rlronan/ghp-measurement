from django.urls import path

from . import views

app_name = 'measure'
urlpatterns = [
    path('', views.index_view, name='index'),
    #path('', views.IndexView.as_view(), name='index'),

    # the 'name' value as called by the {% url %} template tag
    # to change the url, modifiy the path() argument here
    path('<int:ghp_user_id>/', views.ghp_user_piece_view, name='ghp_user_piece_view'), #as_view()
    path('<int:ghp_user_id>/account', views.ghp_user_account_view, name='ghp_user_account_view'), #as_view()
    #path('<int:pk>/email/', views.email, name='email'),
    path('<int:ghp_user_id>/piece/', views.PieceView, name='piece'),
]