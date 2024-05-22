from django.urls import path
from django.urls import path, include  
from . import views
from .views import filter_movies

urlpatterns = [
    path('', views.home, name='index'),
    path('signup/', views.signUp, name='signup'),
    path('login/', views.Login, name='login'),
    path('logout/', views.Logout, name='logout'),
    path('<int:movie_id>/', views.detail, name='detail'),
    path('watch/', views.watch, name='watch'),
    path('recommend/', views.recommend, name='recommend'),
    path('oauth/', include('social_django.urls', namespace='social')),  # Thêm dòng này để sử dụng URL của social_django
    path('profile/', views.profile, name='profile'),  # Trang hồ sơ người dùng
    path('profile/edit/', views.profile_edit, name='profile_edit'),  # Trang chỉnh sửa hồ sơ
    path('oauth/', include('social_django.urls', namespace='social')),  # Thêm dòng này để sử dụng URL của social_django
    path('upgrade_vip/', views.upgrade_vip, name='upgrade_vip'),
    path('user/<str:username>/', views.user_list, name='user_list'),
    path('filter/', filter_movies, name='filter_movies'),
]