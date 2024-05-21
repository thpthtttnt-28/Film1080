from django.urls import path
from django.urls import path, include  
from . import views

urlpatterns = [
    path('', views.home, name='index'),
    path('signup/', views.signUp, name='signup'),
    path('login/', views.Login, name='login'),
    path('logout/', views.Logout, name='logout'),
    path('<int:movie_id>/', views.detail, name='detail'),
    path('watch/', views.watch, name='watch'),
    path('recommend/', views.recommend, name='recommend'),
    path('info/', views.info, name='info'),
    path('oauth/', include('social_django.urls', namespace='social')),  # Thêm dòng này để sử dụng URL của social_django
]