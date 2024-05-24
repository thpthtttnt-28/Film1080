from django.contrib.auth import authenticate, login
from django.contrib.auth import logout
from django.shortcuts import render, get_object_or_404, redirect
from .forms import *
from django.http import Http404
from .models import Movie, Myrating, MyList
from django.db.models import Q, Avg, Count
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.db.models import Case, When
import pandas as pd
from .algo_rcm import get_similar, SearchEngineRecommender, get_trending_movies, RecentRecommender
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Case, When
from django.contrib import messages
from django.http import HttpResponseRedirect, Http404
import pandas as pd
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, get_object_or_404, redirect
from .forms import SignUpForm, UserProfileForm
from .models import Movie, Myrating, MyList, UserProfile
from django.db.models import Q, Case, When
from django.contrib import messages
from django.http import HttpResponseRedirect, Http404
import pandas as pd
from django.contrib.auth.decorators import login_required
from social_django.utils import load_strategy, load_backend
from social_core.backends.google import GoogleOAuth2
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import authenticate, login as auth_login
from django.http import HttpResponseForbidden
from datetime import datetime, timedelta
from django.utils import timezone
from .models import Movie, Myrating, MyList, UserProfile,Comment
from .models import Report
from .models import Movie
from django.core.paginator import Paginator
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import os
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from paypalcheckoutsdk.core import PayPalHttpClient, SandboxEnvironment
from paypalcheckoutsdk.orders import OrdersCreateRequest
from dotenv import load_dotenv
from django.http import HttpResponse
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

# Create your views here.
def index(request):
    movies = Movie.objects.all()
    query = request.GET.get('q')

    if query:
        movies = Movie.objects.filter(Q(title__icontains=query)).distinct()
        return render(request, 'recommend/list.html', {'movies': movies})

    return render(request, 'recommend/list.html', {'movies': movies})

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
        recent_movies = recent_rcm.recommend(top_n=18)

        # if genre:
        #     recent_movies = [movie for movie in recent_movies if movie.genre == genre]

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
    recommended_movie_ids = recommender.recommend(first_movie_genre, k=18)
    movies_similar = Movie.objects.filter(id__in=recommended_movie_ids)

    return render(request, 'recommend/search_movies.html', {'movies': movies,
                                                            'movies_similar': movies_similar})

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
def get_similar(movie_name, rating, corrMatrix):
    similar_ratings = corrMatrix[movie_name] * (rating - 2.5)
    similar_ratings = similar_ratings.sort_values(ascending=False)
    return similar_ratings

# Recommendation Algorithm
@login_required
def recommend(request):
    if request.user.userprofile.is_vip:
        movie_rating = pd.DataFrame(list(Myrating.objects.all().values()))

        new_user = movie_rating.user_id.unique().shape[0]
        current_user_id = request.user.id
        # Kiểm tra nếu người dùng mới không đánh giá bất kỳ bộ phim nào
        if current_user_id > new_user:
            movie = Movie.objects.get(id=19)  # ID của bộ phim mặc định
            q = Myrating(user=request.user, movie=movie, rating=0)
            q.save()

        userRatings = movie_rating.pivot_table(index=['user_id'], columns=['movie_id'], values='rating')
        userRatings = userRatings.fillna(0, axis=1)
        corrMatrix = userRatings.corr(method='pearson')

        user = pd.DataFrame(list(Myrating.objects.filter(user=request.user).values())).drop(['user_id', 'id'], axis=1)
        user_filtered = [tuple(x) for x in user.values]
        movie_id_watched = [each[0] for each in user_filtered]

        similar_movies = pd.DataFrame()
        for movie, rating in user_filtered:
            similar_movies = pd.concat([similar_movies, get_similar(movie, rating, corrMatrix)], axis=1)

        similar_movies = similar_movies.sum(axis=1).sort_values(ascending=False)
        movies_id_recommend = [each for each in similar_movies.index if each not in movie_id_watched]
        preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(movies_id_recommend)])
        movie_list = list(Movie.objects.filter(id__in=movies_id_recommend).order_by(preserved)[:10])

        context = {'movie_list': movie_list}
        return render(request, 'recommend/recommend.html', context)
    else:
        messages.error(request, "Only VIP users can access recommendations.")
        return redirect('profile')


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
                return redirect("index")
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
        user_profile = request.user.userprofile
        # Cập nhật trạng thái VIP của người dùng
        user_profile.is_vip = True
        user_profile.save()
        
        return redirect('profile')
    
    return render(request, 'recommend/upgrade_vip.html')

def upgrade_to_vip(request):
    # Xử lý thông tin từ form
    
    # Tạo environment PayPal Sandbox
    environment = SandboxEnvironment(client_id="YOUR_PAYPAL_CLIENT_ID", client_secret="YOUR_PAYPAL_CLIENT_SECRET")
    client = PayPalHttpClient(environment)
    
    # Tạo đơn hàng PayPal
    request = OrdersCreateRequest()
    request.prefer("return=representation")
    request.request_body({
        "intent": "CAPTURE",
        "purchase_units": [{
            "amount": {
                "currency_code": "USD",
                "value": "10.00"  # Giá trị của VIP
            }
        }]
    })
    
    # Gửi yêu cầu đến PayPal và nhận về link thanh toán
    response = client.execute(request)
    return HttpResponseRedirect(response.result.links[1].href)


class PayPalClient:
    def __init__(self):
        self.client_id = os.getenv('PAYPAL_CLIENT_ID')
        self.client_secret = os.getenv('PAYPAL_CLIENT_SECRET')
        self.environment = SandboxEnvironment(client_id=self.client_id, client_secret=self.client_secret)
        self.client = PayPalHttpClient(self.environment)

@csrf_exempt
def upgrade_to_vip(request):
    if request.method == 'POST':
        # Lấy giá trị vip_duration từ POST request
        amount = "10.00"  # Giá trị mặc định

        # Kiểm tra xem người dùng chọn "Pay manually" hay "Pay with PayPal"
        if request.POST.get('payment_method') == 'manual':
            request.user.userprofile.is_vip = True
            request.userprofile.save()
            
            # Chuyển hướng người dùng đến trang thành công hoặc trang cần thiết
            return redirect('success')   # Chỉ định URL thành công của bạn

        else:
            # Nếu người dùng chọn "Pay with PayPal", chuyển hướng đến PayPal để thực hiện thanh toán
            paypal_client = PayPalClient()
            request = OrdersCreateRequest()
            request.prefer("return=representation")
            request.request_body({
                "intent": "CAPTURE",
                "purchase_units": [{
                    "amount": {
                        "currency_code": "USD",
                        "value": amount
                    }
                }]
            })

            response = paypal_client.client.execute(request)
            for link in response.result.links:
                if link.rel == "approve":
                    approval_url = link.href
                    return redirect(approval_url)

    return redirect('upgrade_vip')

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



