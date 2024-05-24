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
        
    def recommend(self, genre, k=20):
        if self.model is None:
            self.train_model()
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

    def recommend(self, top_n=18):
        watched_movies = self._get_watched_movies()
        print(watched_movies)
        if len(watched_movies) == 0:
            return self._get_popular_movies(top_n)
        if len(watched_movies) > 1000:  # Adjust this threshold as needed
            watched_movies = watched_movies[:1000]
        recommendations = self._generate_recommendations(watched_movies)
        if not recommendations:
            return self._get_popular_movies(top_n)
        return self._get_top_n_recommendations(recommendations, top_n)

    def _get_watched_movies(self):
        watched = MyList.objects.filter(user=self.user, watch=True).values_list('movie_id', flat=True)
        return list(watched)

    def _generate_recommendations(self, watched_movies):
        recommendations = {}
        for movie in watched_movies:
            if movie in self.co_occurrence_matrix:
                for co_movie, score in self.co_occurrence_matrix[movie].items():
                    if co_movie not in watched_movies:
                        recommendations[co_movie] = recommendations.get(co_movie, 0) + score
        return recommendations

    def _get_top_n_recommendations(self, recommendations, top_n):
        sorted_recommendations = sorted(recommendations.items(), key=lambda item: item[1], reverse=True)
        top_recommendations = sorted_recommendations[:top_n]
        top_movie_ids = [movie_id for movie_id, score in top_recommendations]
        return Movie.objects.filter(id__in=top_movie_ids)

    def _get_popular_movies(self, top_n):
        # Gợi ý phim theo số lượt xem trong bảng MyList
        trending_movie_ids = MyList.objects.values('movie').annotate(total_watch=Count('movie')).order_by('-total_watch')[:12]
        trending_movies = Movie.objects.filter(id__in=[movie['movie'] for movie in trending_movie_ids])
        return trending_movies
    
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