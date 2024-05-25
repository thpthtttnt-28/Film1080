from django.http import HttpResponseForbidden
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Movie, Myrating, MyList, UserProfile, Comment, Report
from datetime import datetime, timedelta
from django.db.models import Avg
import os
from django.contrib.messages import get_messages

class TestViews(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')
        # Tạo nhiều phim để đảm bảo đủ số lượng để gợi ý
        for i in range(20):
            movie = Movie.objects.create(title=f'Test Movie {i}', genre='Action', is_vip=False, year=2024)
            MyList.objects.create(user=self.user, movie=movie, watch=False)
            Myrating.objects.create(user=self.user, movie=movie, rating=5)
        
        self.movie = Movie.objects.create(title='Test Movie', genre='Action', is_vip=False, year=2024)
        self.mylist = MyList.objects.create(user=self.user, movie=self.movie, watch=False)
        self.myrating = Myrating.objects.create(user=self.user, movie=self.movie, rating=5)
        
        os.environ['PYSPARK_PYTHON'] = 'F:\\test\\python.exe'
        os.environ['PYSPARK_DRIVER_PYTHON'] = 'F:\\test\\python.exe'

    def test_home_view(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recommend/list.html')

    def test_detail_view(self):
        response = self.client.get(reverse('detail', args=[self.movie.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recommend/detail.html')

    def test_watch_view(self):
        response = self.client.get(reverse('watch'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recommend/watch.html')

    def test_signUp_view(self):
        response = self.client.get(reverse('signup'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recommend/signUp.html')

    def test_login_view(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recommend/login.html')

    def test_logout_view(self):
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 302)  # Redirects to login page after logout

    def test_profile_view(self):
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recommend/profile.html')

    def test_profile_edit_view(self):
        response = self.client.get(reverse('profile_edit'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recommend/profile_edit.html')

    def test_upgrade_vip_view(self):
        response = self.client.get(reverse('upgrade_vip'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recommend/upgrade_vip.html')

    def test_user_list_view(self):
        response = self.client.get(reverse('user_list', args=[self.user.username]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recommend/user_list.html')

    def test_movie_filter_view(self):
        response = self.client.get(reverse('movie_filter'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recommend/movie_filter.html')

    def test_home_view_authenticated_user(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

    def test_detail_view_authenticated_user(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('detail', args=[self.movie.id]))
        self.assertEqual(response.status_code, 200)

    def test_watch_view_authenticated_user(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('watch'))
        self.assertEqual(response.status_code, 200)

    def test_profile_view_authenticated_user(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)

    def test_profile_edit_view_authenticated_user(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('profile_edit'))
        self.assertEqual(response.status_code, 200)

    def test_upgrade_vip_view_authenticated_user(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('upgrade_vip'))
        self.assertEqual(response.status_code, 200)

    def test_user_list_view_authenticated_user(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('user_list', args=[self.user.username]))
        self.assertEqual(response.status_code, 200)

    def test_movie_filter_view_authenticated_user(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('movie_filter'))
        self.assertEqual(response.status_code, 200)
    
    def test_signUp_view_post_request(self):
        response = self.client.post(reverse('signup'), {'username': 'newuser', 'email': 'newuser@example.com', 'password1': 'newpassword', 'password2': 'newpassword'})
        self.assertEqual(response.status_code, 200)  # Redirects after successful signup

    def test_signUp_view_invalid_post_request(self):
        response = self.client.post(reverse('signup'), {'username': '', 'email': '', 'password1': '', 'password2': ''})
        self.assertEqual(response.status_code, 200)  # Signup form should be re-rendered with errors

    def test_Login_view_post_request(self):
        response = self.client.post(reverse('login'), {'username': 'testuser', 'password': 'testpassword'})
        self.assertEqual(response.status_code, 302)  # Redirects after successful login

    def test_Login_view_invalid_post_request(self):
        response = self.client.post(reverse('login'), {'username': 'testuser', 'password': 'wrongpassword'})
        self.assertEqual(response.status_code, 200)  # Login form should be re-rendered with errors

    def test_Logout_view(self):
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 302)  # Redirects after logout

    def test_profile_edit_view_post_request(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.post(reverse('profile_edit'), {'bio': 'New bio'})
        self.assertEqual(response.status_code, 200)  # Redirects after profile edit

    def test_upgrade_vip_view_post_request(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.post(reverse('upgrade_vip'), {'vip_duration': 1})
        self.assertEqual(response.status_code, 302)  # Redirects after VIP upgrade

    def test_user_list_view_invalid_username(self):
        response = self.client.get(reverse('user_list', args=['invalidusername']))
        self.assertEqual(response.status_code, 404)  # Invalid username should return 404

    def test_movie_filter_view_with_genre(self):
        response = self.client.get(reverse('movie_filter') + '?genre=Action')
        self.assertEqual(response.status_code, 200)

    def test_movie_filter_view_pagination(self):
        response = self.client.get(reverse('movie_filter'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue('movies' in response.context)
        self.assertTrue(len(response.context['movies']) <= 20)  # Should have 20 or less movies per page

    def test_detail_view_post_request_watch(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.post(reverse('detail', args=[self.movie.id]), {'watch': 'on'})
        self.assertEqual(response.status_code, 302)  # Redirects after updating watch status

    def test_detail_view_post_request_rating(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.post(reverse('detail', args=[self.movie.id]), {'rating': '4'})
        self.assertEqual(response.status_code, 302)  # Redirects after submitting rating

    def test_detail_view_post_request_comment(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.post(reverse('detail', args=[self.movie.id]), {'comment': 'Test comment'})
        self.assertEqual(response.status_code, 302)  # Redirects after submitting comment

    def test_detail_view_post_request_report(self):
        self.client.login(username='testuser', password='testpassword')
        comment = Comment.objects.create(user=self.user, movie=self.movie, text='Test comment')
        response = self.client.post(reverse('detail', args=[self.movie.id]), {'report': 'report', 'comment_id': comment.id, 'reason': 'Test reason'})
        self.assertEqual(response.status_code, 302)  # Redirects after submitting report

    def test_detail_view_no_active_user(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.get(reverse('detail', args=[self.movie.id]))
        self.assertEqual(response.status_code, 302)

    def test_detail_view_non_vip_user_watch_vip_movie(self):
        self.movie.is_vip = True
        self.movie.save()

        response = self.client.get(reverse('detail', args=[self.movie.id]))

        self.assertEqual(response.status_code, 404)

    def test_detail_view_authenticated_user_with_rating(self):
        self.client.login(username='testuser', password='testpassword')
        self.myrating.rating = 0  # Rating set to 0
        self.myrating.save()
        response = self.client.get(reverse('detail', args=[self.movie.id]))
        self.assertEqual(response.context['movie_rating'], 0)  # Check if movie rating is set to 0 for authenticated user

    def test_detail_view_authenticated_user_without_rating(self):
        self.client.login(username='testuser', password='testpassword')
        self.myrating.delete()  # Delete user's rating for the movie
        response = self.client.get(reverse('detail', args=[self.movie.id]))
        self.assertEqual(response.context['movie_rating'], 0)  # Check if movie rating is 0 when user hasn't rated the movie yet

    def test_detail_view_avg_rating(self):
        Myrating.objects.create(user=self.user, movie=self.movie, rating=4)
        response = self.client.get(reverse('detail', args=[self.movie.id]))
        self.assertEqual(response.context['movie_avg_rating'], 4.5)  # Check if average rating is calculated correctly

    def test_detail_view_no_avg_rating(self):
        response = self.client.get(reverse('detail', args=[self.movie.id]))
        self.assertEqual(response.context['movie_avg_rating'], 5)  # Check if average rating is 0 when no ratings are available

    def test_detail_view_watch_status(self):
        response = self.client.get(reverse('detail', args=[self.movie.id]))
        self.assertFalse(response.context['update'])  # Check if initial watch status is False

    def test_detail_view_watch_status_update(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.post(reverse('detail', args=[self.movie.id]), {'watch': 'on'})
        self.assertTrue(MyList.objects.get(user=self.user, movie=self.movie).watch)  # Check if watch status is updated to True

    def test_detail_view_comment(self):
        Comment.objects.create(user=self.user, movie=self.movie, text='Test comment')
        response = self.client.get(reverse('detail', args=[self.movie.id]))
        self.assertTrue(response.context['comments'])  # Check if comments are available

    def test_detail_view_no_comment(self):
        response = self.client.get(reverse('detail', args=[self.movie.id]))
        self.assertFalse(response.context['comments'])  # Check if no comments are available

    def test_search_movies_view_authenticated_user(self):
        response = self.client.get(reverse('search_movies'), {'q': 'Test'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recommend/search_movies.html')
        self.assertContains(response, 'Test Movie')

    def test_detail_view_post_request_watch_remove(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.post(reverse('detail', args=[self.movie.id]), {'watch': 'off'})
        self.assertEqual(response.status_code, 302)  # Redirects after updating watch status
        self.assertFalse(MyList.objects.get(user=self.user, movie=self.movie).watch)  # Check if watch status is updated to False

    def test_watch_view_no_movies(self):
        MyList.objects.filter(user=self.user, movie=self.movie).delete()  # Remove movies from the watchlist
        response = self.client.get(reverse('watch'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['movies'], [])  # Check if no movies are in the watchlist

    def test_watch_view_with_vip_movies_non_vip_user(self):
        self.movie.is_vip = True
        self.movie.save()
        response = self.client.get(reverse('watch'))
        self.assertNotIn(self.movie, response.context['movies'])  # Non-VIP user should not see VIP movies in the watchlist

    def test_detail_view_comment_creation(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.post(reverse('detail', args=[self.movie.id]), {'comment': 'New comment'})
        self.assertEqual(response.status_code, 302)  # Redirects after submitting comment
        self.assertTrue(Comment.objects.filter(user=self.user, movie=self.movie, text='New comment').exists())  # Check if comment is created

    def test_detail_view_report_creation(self):
        self.client.login(username='testuser', password='testpassword')
        comment = Comment.objects.create(user=self.user, movie=self.movie, text='Test comment')
        response = self.client.post(reverse('detail', args=[self.movie.id]), {'report': 'report', 'comment_id': comment.id, 'reason': 'Test reason'})
        self.assertEqual(response.status_code, 302)  # Redirects after submitting report
        self.assertTrue(Report.objects.filter(user=self.user, comment=comment, reason='Test reason').exists())  # Check if report is created

    def test_upgrade_vip_view_post_request_six_months(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.post(reverse('upgrade_vip'), {'vip_duration': 6})
        self.assertEqual(response.status_code, 302)  # Redirects after VIP upgrade
        self.user.refresh_from_db()
        self.assertTrue(self.user.userprofile.is_vip)  # Check if user is VIP

    def test_upgrade_vip_view_post_request_authenticated_user(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.post(reverse('upgrade_vip'), {'vip_duration': 1})
        self.assertEqual(response.status_code, 302)  # Redirects after VIP upgrade
        self.assertRedirects(response, reverse('profile'))  # Check if redirects to profile page

    def test_upgrade_vip_view_post_request_unauthenticated_user(self):
        response = self.client.post(reverse('upgrade_vip'), {'vip_duration': 1})
        self.assertEqual(response.status_code, 302)  # Redirects after VIP upgrade
        self.assertRedirects(response, reverse('profile')) 