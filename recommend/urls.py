from django.urls import include, path
from .views import HomeView
from .account import (
    SignUp, Login, Logout, Profile, ProfileEdit, UserList
)

from .upgrade_vip import UpgradeVIP, UpgradeToVIP

from .movies_view import MovieDetailView, WatchListView, MovieFilterView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('movie/<int:pk>/', MovieDetailView.as_view(), name='detail'),
    path('watch/', WatchListView.as_view(), name='watch'),
    path('signup/', SignUp.as_view(), name='signup'),
    path('login/', Login.as_view(), name='login'),
    path('logout/', Logout.as_view(), name='logout'),
    path('profile/', Profile.as_view(), name='profile'),
    path('profile/edit/', ProfileEdit.as_view(), name='profile_edit'),
    path('upgrade_vip/', UpgradeVIP.as_view(), name='upgrade_vip'),
    path('upgrade_to_vip/', UpgradeToVIP.as_view(), name='paypal_payment'),
    path('user/<str:username>/', UserList.as_view(), name='user_list'),
    path('filter/', MovieFilterView.as_view(), name='movie_filter'),
    path('oauth/', include('social_django.urls', namespace='social')),
    path('search/', HomeView.as_view(), name='search_movies'),
]
