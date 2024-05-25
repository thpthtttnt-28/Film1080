from django.views import View
from django.views.generic import DetailView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.contrib import messages
from django.http import HttpResponseRedirect, Http404
from django.core.paginator import Paginator
from django.db.models import Q, Avg
from .models import Movie, Myrating, MyList, Comment, Report

class MovieDetailView(LoginRequiredMixin, DetailView):
    model = Movie
    template_name = 'recommend/detail.html'
    context_object_name = 'movie'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        movie_id = self.kwargs['pk']
        movie = self.get_object()
        user = self.request.user

        if not user.userprofile.is_vip and movie.is_vip:
            raise Http404("Only VIP members can access this movie.")

        try:
            watch_item = MyList.objects.get(movie_id=movie_id, user=user)
            context['update'] = watch_item.watch
        except MyList.DoesNotExist:
            context['update'] = False

        user_rating = Myrating.objects.filter(movie_id=movie_id, user=user).first()
        context['movie_rating'] = user_rating.rating if user_rating else 0
        context['rate_flag'] = user_rating is not None

        context['comments'] = Comment.objects.filter(movie=movie).order_by('-created_at')
        context['movie_avg_rating'] = Myrating.objects.filter(movie_id=movie_id).aggregate(Avg('rating'))['rating__avg'] or 0

        return context

    def post(self, request, *args, **kwargs):
        movie = self.get_object()
        user = request.user

        if 'watch' in request.POST:
            watch_flag = request.POST['watch']
            update = watch_flag == 'on'
            mylist, created = MyList.objects.get_or_create(movie_id=movie.id, user=user)
            mylist.watch = update
            mylist.save()
            messages.success(request, "Movie added to your list!" if update else "Movie removed from your list!")

        elif 'rating' in request.POST:
            rate = request.POST['rating']
            rating, created = Myrating.objects.get_or_create(movie_id=movie.id, user=user)
            rating.rating = rate
            rating.save()
            messages.success(request, "Rating has been submitted!")

        elif 'comment' in request.POST:
            comment_text = request.POST['comment']
            Comment.objects.create(user=user, movie=movie, text=comment_text)
            messages.success(request, "Comment has been submitted!")

        elif 'report' in request.POST:
            comment_id = request.POST['comment_id']
            reason = request.POST['reason']
            comment = get_object_or_404(Comment, id=comment_id)
            Report.objects.create(user=user, comment=comment, reason=reason)
            messages.success(request, "Report has been submitted!")

        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

class WatchListView(LoginRequiredMixin, ListView):
    template_name = 'recommend/watch.html'
    context_object_name = 'movies'

    def get_queryset(self):
        user = self.request.user
        query = self.request.GET.get('q')
        if user.userprofile.is_vip:
            movies = Movie.objects.filter(mylist__watch=True, mylist__user=user)
        else:
            movies = Movie.objects.filter(mylist__watch=True, mylist__user=user, is_vip=False)

        if query:
            movies = movies.filter(Q(title__icontains=query)).distinct()

        return movies

class MovieFilterView(View):
    def get(self, request, *args, **kwargs):
        genre = request.GET.get('genre')
        movies = Movie.objects.all()

        if genre:
            movies = movies.filter(genre__icontains=genre)

        paginator = Paginator(movies, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = {
            'movies': page_obj,
        }

        return render(request, 'recommend/movie_filter.html', context)