from .forms import *
from django.db.models import Q, Avg, Count, Case, When
from django.contrib import messages
import pandas as pd
from .algo_rcm import get_similar, SearchEngineRecommender, get_trending_movies, RecentRecommender
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect, Http404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from .forms import SignUpForm, UserProfileForm
from .models import Movie, Myrating, MyList, UserProfile
from social_django.utils import load_strategy, load_backend
from social_core.backends.google import GoogleOAuth2
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseForbidden
from datetime import datetime, timedelta
from .models import Movie, Myrating, MyList, UserProfile, Comment
from .models import Report
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

# Create your views here.
def home(request):
    # Gợi ý phim theo số lượt xem
    trending_movies = get_trending_movies()

    # Lấy thể loại phim từ yêu cầu GET
    genre = request.GET.get('genre')

    query = request.GET.get('q')

    if query:
        movies = Movie.objects.filter(Q(title__icontains=query)).distinct()
        if movies.exists():
            return search_movies(request, movies)
        
    # Kiểm tra xem người dùng đã đăng nhập chưa
    if request.user.is_authenticated:
        recent_rcm = RecentRecommender(request.user)
        recent_movies = recent_rcm.recommend(top_n=12)

        if genre:
            recent_movies = [movie for movie in recent_movies if movie.genre == genre]

        context = {
            'trending_movies': trending_movies,
            'recent_movies': recent_movies,
        }
        return render(request, 'recommend/list.html', context)

    # Lọc phim theo thể loại nếu có
    if genre:
        trending_movies = trending_movies.filter(genre=genre)

    # Trả về trang chủ chỉ với danh sách các phim phổ biến hoặc danh sách phim theo thể loại
    context = {
        'trending_movies': trending_movies,
    }
    return render(request, 'recommend/list.html', context)

def search_movies(request, movies):
    # Lấy genre của bộ phim đầu tiên tìm thấy
    first_movie_genre = movies.first().genre
    # Khởi tạo SearchEngineRecommender và gợi ý các phim tương tự
    recommender = SearchEngineRecommender()
    recommended_movie_ids = recommender.recommend(first_movie_genre, k=12)
    movies_similar = Movie.objects.filter(id__in=recommended_movie_ids)

    return render(request, 'recommend/search_movies.html', {'movies': movies,
                                                            'movies_similar': movies_similar})
def search_movies_wrapper(request):
    query = request.GET.get('q', '')
    movies = Movie.objects.filter(title__icontains=query)
    return search_movies(request, movies)

# Show details of the movie
def detail(request, movie_id):
    if not request.user.is_authenticated:
        return redirect("login")
    if not request.user.is_active:
        raise Http404

    movie = get_object_or_404(Movie, id=movie_id)
    
    # Kiểm tra xem người dùng có phải là thành viên VIP hay không
    if not request.user.userprofile.is_vip and movie.is_vip:
        return HttpResponseForbidden("Only VIP members can access this movie.")
    
    # Code tiếp tục như bình thường
    temp = list(MyList.objects.filter(movie_id=movie_id, user=request.user).values())
    update = temp[0]['watch'] if temp else False

    if request.method == "POST":
        if 'watch' in request.POST:
            watch_flag = request.POST['watch']
            update = watch_flag == 'on'
            if MyList.objects.filter(movie_id=movie_id, user=request.user).exists():
                MyList.objects.filter(movie_id=movie_id, user=request.user).update(watch=update)
            else:
                MyList(user=request.user, movie=movie, watch=update).save()
            messages.success(request, "Movie added to your list!" if update else "Movie removed from your list!")
        elif 'rating' in request.POST:
            rate = request.POST['rating']
            if Myrating.objects.filter(movie_id=movie_id, user=request.user).exists():
                Myrating.objects.filter(movie_id=movie_id, user=request.user).update(rating=rate)
            else:
                Myrating(user=request.user, movie=movie, rating=rate).save()
            messages.success(request, "Rating has been submitted!")
        elif 'comment' in request.POST:
            comment_text = request.POST['comment']
            Comment(user=request.user, movie=movie, text=comment_text).save()
            messages.success(request, "Comment has been submitted!")
        elif 'report' in request.POST:
            comment_id = request.POST['comment_id']
            reason = request.POST['reason']
            comment = get_object_or_404(Comment, id=comment_id)
            Report(user=request.user, comment=comment, reason=reason).save()
            messages.success(request, "Report has been submitted!")

        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    out = list(Myrating.objects.filter(user=request.user.id).values())
    movie_rating = 0
    rate_flag = False
    for each in out:
        if each['movie_id'] == movie_id:
            movie_rating = each['rating']
            rate_flag = True
            break

    comments = Comment.objects.filter(movie=movie).order_by('-created_at')

    # Tính toán rating trung bình
    avg_rating = Myrating.objects.filter(movie_id=movie_id).aggregate(Avg('rating'))['rating__avg']
    
    # Nếu không có rating, gán giá trị mặc định là 0
    movie_avg_rating = avg_rating if avg_rating else 0

    context = {
        'movie': movie,
        'movie_rating': movie_rating,
        'rate_flag': rate_flag,
        'update': update,
        'comments': comments,
        'movie_avg_rating': movie_avg_rating,
    }

    return render(request, 'recommend/detail.html', context)

# MyList functionality
@login_required
def watch(request):
    try:
        user_profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        # Create UserProfile if it does not exist
        user_profile = UserProfile.objects.create(user=request.user)
    
    if user_profile.is_vip:
        movies = Movie.objects.filter(mylist__watch=True, mylist__user=request.user)
    else:
        movies = Movie.objects.filter(mylist__watch=True, mylist__user=request.user, is_vip=False)

    query = request.GET.get('q')

    if query:
        movies = movies.filter(Q(title__icontains=query)).distinct()

    return render(request, 'recommend/watch.html', {'movies': movies})

# Register user
def signUp(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Đăng nhập người dùng với backend mặc định của Django
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('profile')  # Điều hướng đến trang profile sau khi đăng ký thành công
    else:
        form = SignUpForm()
    return render(request, 'recommend/signUp.html', {'form': form})


# Login User
def Login(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)

        if user is not None:
            if user.is_active:
                login(request, user)
                # Chuyển hướng đến trang chính sau khi đăng nhập thành công
                return redirect("home")
            else:
                return render(request, 'recommend/login.html', {'error_message': 'Your account is disabled'})
        else:
            return render(request, 'recommend/login.html', {'error_message': 'Invalid Login'})

    return render(request, 'recommend/login.html')


# Logout user
def Logout(request):
    logout(request)
    return redirect("login")

# Profile view
@login_required
def profile(request):
    user = request.user
    user_profile = None
    user_full_name = None

    # Kiểm tra xem UserProfile có tồn tại không
    if hasattr(user, 'userprofile'):
        user_profile = user.userprofile

    # Lấy tên đầy đủ của người dùng
    user_full_name = user.get_full_name()

    return render(request, 'recommend/profile.html', {'user_profile': user_profile, 'user_full_name': user_full_name})

# Profile edit view
@login_required
def profile_edit(request):
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=user_profile)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = UserProfileForm(instance=user_profile)
    return render(request, 'recommend/profile_edit.html', {'form': form})

@login_required
def upgrade_vip(request):
    if request.method == 'POST':
        vip_duration = int(request.POST.get('vip_duration'))
        user_profile = request.user.userprofile
        
        # Cập nhật trạng thái VIP của người dùng
        user_profile.is_vip = True
        
        # Xác định thời gian hết hạn của gói VIP dựa trên loại gói
        if vip_duration == 1:
            expire_date = datetime.now() + timedelta(days=30)
        elif vip_duration == 6:
            expire_date = datetime.now() + timedelta(days=180)
        elif vip_duration == 12:
            expire_date = datetime.now() + timedelta(days=365)
        
        # Lưu lại thời gian hết hạn vào cơ sở dữ liệu
        user_profile.vip_expire_date = expire_date
        user_profile.save()
        
        return redirect('profile')

    return render(request, 'recommend/upgrade_vip.html')

def user_list(request, username):
    user = get_object_or_404(User, username=username)
    movies = MyList.objects.filter(user=user).select_related('movie')
    return render(request, 'recommend/user_list.html', {'user': user, 'movies': movies})

def movie_filter(request):
    genre = request.GET.get('genre')
    movies = Movie.objects.all()
    
    if genre:
        movies = movies.filter(genre__icontains=genre)

    paginator = Paginator(movies, 20)  # 20 movies per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'movies': page_obj,
    }

    return render(request, 'recommend/movie_filter.html', context)




