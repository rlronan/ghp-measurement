from django.urls import path

from . import views

app_name = 'measure'
urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    # the 'name' value as called by the {% url %} template tag
    # to change the url, modifiy the path() argument here
    path('<int:ghp_user_id>/', views.GHPUserView, name='ghp_user'), #as_view()
    #path('<int:pk>/email/', views.email, name='email'),
    path('<int:ghp_user_id>/piece/', views.PieceView, name='piece'),
]