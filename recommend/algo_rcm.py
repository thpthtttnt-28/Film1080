import os
import numpy as np
import pandas as pd
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD
from scipy.sparse import coo_matrix
from .models import Movie, MyList, Myrating, User
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
from django.db.models import Q, Avg, Count, Case, When
from .coOccurenceMatrixGenerator import CoOccurrenceMatrixGenerator
from .models import CachedModel
import pickle

class SearchEngineRecommender:
    def __init__(self):
        self.movies_df = pd.DataFrame(list(Movie.objects.all().values('id', 'title', 'genre')))
        self.model = None
        self.mlb = MultiLabelBinarizer()

    def preprocess_genres(self):
        # Tách các thể loại cách nhau bằng dấu phẩy
        self.movies_df['genre'] = self.movies_df['genre'].apply(lambda x: x.split(', '))
        self.genre_matrix = self.mlb.fit_transform(self.movies_df['genre'])


    def train_model(self):
        # Preprocess genres before creating the model
        self.preprocess_genres()
        # Train kNN model
        self.model = NearestNeighbors(metric='euclidean', algorithm='brute')
        self.model.fit(self.genre_matrix)
        # Save model to database
        model_bytes = pickle.dumps(self.model)  # Convert model to bytes
        CachedModel.objects.create(model_state=model_bytes)

    def get_cached_model(self):
        cached_model = CachedModel.objects.last()  # Get the last saved model
        if cached_model:
            model_bytes = cached_model.model_state
            return pickle.loads(model_bytes)  # Convert bytes back to model object
        return None
        
    def recommend(self, genre, k=20):
        cached_model = self.get_cached_model()
        if cached_model:
            self.model = cached_model
        else:
            self.train_model()
        self.preprocess_genres()
        # Tách các thể loại trong query
        genre_list = genre.split(', ')
        genre_vector = self.mlb.transform([genre_list])

        distances, indices = self.model.kneighbors(genre_vector, n_neighbors=k+1)

        # Get recommended movie ids
        recommended_movie_ids = self.movies_df.iloc[indices[0]]['id'].tolist()

        return recommended_movie_ids[1:]

class RecentRecommender:
    def __init__(self, user):
        self.user = user
        self.co_matrix_generator = CoOccurrenceMatrixGenerator()
        self.co_occurrence_matrix = self.co_matrix_generator.get_or_create_matrix()
        self.model = None
        self.mlb = MultiLabelBinarizer()
        self.movies_df = pd.DataFrame(list(Movie.objects.all().values('id', 'title', 'genre')))
        if self.model is None:
            self.load_cached_knn_model()

    def preprocess_genres(self):
        self.movies_df['genre'] = self.movies_df['genre'].apply(lambda x: x.split(', '))
        self.genre_matrix = self.mlb.fit_transform(self.movies_df['genre'])

    def load_cached_knn_model(self):
        cached_model = CachedModel.objects.last()
        if cached_model:
            model_bytes = cached_model.model_state
            self.model = pickle.loads(model_bytes)
        else:
            self.train_knn_model()

    def train_knn_model(self):
        if self.model is None:
            self.preprocess_genres()
            self.model = NearestNeighbors(metric='euclidean', algorithm='brute')
            self.model.fit(self.genre_matrix)

    def recommend(self, top_n=18):
        watched_movies = self._get_watched_movies()
        if not watched_movies:
            return self._get_popular_movies(top_n)
        watched_movies = watched_movies[:1000] if len(watched_movies) > 1000 else watched_movies
        combined_recommendations = self._combine_recommendations(
            self._generate_co_occurrence_recommendations(watched_movies),
            self._generate_knn_recommendations(watched_movies, top_n)
        )
        return self._get_top_n_recommendations(combined_recommendations, top_n)

    def _get_watched_movies(self):
        return list(MyList.objects.filter(user=self.user, watch=True).values_list('movie_id', flat=True))

    def _generate_co_occurrence_recommendations(self, watched_movies):
        recommendations = {}
        for movie in watched_movies:
            if movie in self.co_occurrence_matrix:
                for co_movie, score in self.co_occurrence_matrix[movie].items():
                    if co_movie not in watched_movies:
                        recommendations[co_movie] = recommendations.get(co_movie, 0) + score
        return recommendations

    def _generate_knn_recommendations(self, watched_movies, top_n):
        recommendations = []
        for movie_id in watched_movies:
            movie = Movie.objects.get(id=movie_id)
            genre_list = movie.genre.split(', ')
            genre_vector = self.mlb.transform([genre_list])
            _, indices = self.model.kneighbors(genre_vector, n_neighbors=top_n + 1)
            recommendations.extend(self.movies_df.iloc[indices[0]]['id'].tolist()[1:])
        return recommendations

    def _combine_recommendations(self, co_occurrence_recommendations, knn_recommendations):
        for movie in knn_recommendations:
            co_occurrence_recommendations[movie] = co_occurrence_recommendations.get(movie, 0) + 1
        return co_occurrence_recommendations

    def _get_top_n_recommendations(self, recommendations, top_n):
        sorted_recommendations = sorted(recommendations.items(), key=lambda item: item[1], reverse=True)
        top_movie_ids = [movie_id for movie_id, _ in sorted_recommendations[:top_n]]
        return Movie.objects.filter(id__in=top_movie_ids)

    def _get_popular_movies(self, top_n):
        trending_movie_ids = MyList.objects.values('movie').annotate(total_watch=Count('movie')).order_by('-total_watch')[:12]
        return Movie.objects.filter(id__in=[movie['movie'] for movie in trending_movie_ids])
    
# To get similar movies based on user rating
def get_similar(movie_name,rating,corrMatrix):
    similar_ratings = corrMatrix[movie_name]*(rating-2.5)
    similar_ratings = similar_ratings.sort_values(ascending=False)
    return similar_ratings

def get_trending_movies():
    # Gợi ý phim theo số lượt xem trong bảng MyList
    trending_movie_ids = MyList.objects.values('movie').annotate(total_watch=Count('movie')).order_by('-total_watch')[:12]
    trending_movies = Movie.objects.filter(id__in=[movie['movie'] for movie in trending_movie_ids])
    return trending_movies