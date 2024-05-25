from django.views.generic import TemplateView
from django.db.models import Q

from .models import Movie
from .algo_rcm import SearchEngineRecommender, get_trending_movies, RecentRecommender
import os
from dotenv import load_dotenv
from django.template.response import TemplateResponse

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

class HomeView(TemplateView):
    template_name = 'recommend/list.html'

    def get(self, request, *args, **kwargs):
        trending_movies = get_trending_movies()
        genre = request.GET.get('genre')
        query = request.GET.get('q')

        if query:
            movies = Movie.objects.filter(Q(title__icontains=query)).distinct()
            if movies.exists():
                return self.search_movies(request, movies)

        if request.user.is_authenticated:
            recent_rcm = RecentRecommender(request.user)
            recent_movies = recent_rcm.recommend(top_n=12)
            if genre:
                recent_movies = [movie for movie in recent_movies if movie.genre == genre]

            context = {
                'trending_movies': trending_movies,
                'recent_movies': recent_movies,
            }
            return self.render_to_response(context)

        if genre:
            trending_movies = trending_movies.filter(genre=genre)

        context = {
            'trending_movies': trending_movies,
        }
        return self.render_to_response(context)

    def search_movies(self, request, movies):
        first_movie_genre = movies.first().genre
        recommender = SearchEngineRecommender()
        recommended_movie_ids = recommender.recommend(first_movie_genre, k=12)
        movies_similar = Movie.objects.filter(id__in=recommended_movie_ids)

        return TemplateResponse(request, 'recommend/search_movies.html', {
            'movies': movies,
            'movies_similar': movies_similar
        })
