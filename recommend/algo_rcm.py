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
        # Example: Get the top N popular movies
        return Movie.objects.order_by('-popularity')[:top_n]
    

class CollaborativeFilteringRecommender:
    def __init__(self):
        pass

    def cooccurrence_matrix(self, user_id):
        # Xây dựng ma trận co-occurrence từ dữ liệu trong bảng MyList
        user_watched_movies = MyList.objects.filter(user=user_id, watch=True).values_list('movie', flat=True)
        num_movies = Movie.objects.count()
        row = []
        col = []
        data = []

        for movie_id in user_watched_movies:
            movie_watched = MyList.objects.filter(movie=movie_id, watch=True).values_list('user', flat=True)
            for watched_user_id in movie_watched:
                if watched_user_id != user_id:  # Loại bỏ người dùng hiện tại khỏi ma trận co-occurrence
                    user_watched_movies_of_watched_user = MyList.objects.filter(user=watched_user_id, watch=True).exclude(movie=movie_id).values_list('movie', flat=True)
                    for watched_movie_id in user_watched_movies_of_watched_user:
                        row.append(movie_id - 1)
                        col.append(watched_movie_id - 1)
                        data.append(1)

        cooccurrence_matrix = coo_matrix((data, (row, col)), shape=(num_movies, num_movies))

        return cooccurrence_matrix
    
    def get_cooccurrence_matrix_recommendation(self, user_id, k=20):
        # Gợi ý phim dựa trên co-occurrence matrix
        cooccurrence_matrix = self.cooccurrence_matrix(user_id)
        co_movies = []

        # Lấy danh sách các phim đã xem bởi user hiện tại
        user_watched_movies = MyList.objects.filter(user=user_id, watch=True).values_list('movie', flat=True)

        # Tính điểm tương tự giữa các phim và chọn ra những phim có điểm tương tự cao nhất
        for movie_id in user_watched_movies:
            similar_movies = cooccurrence_matrix.getrow(movie_id - 1).toarray().flatten()
            similar_movie_ids = [i + 1 for i, sim in enumerate(similar_movies) if sim > 0]
            co_movies.extend(similar_movie_ids)

        # Lọc ra các phim không trùng lặp và không nằm trong danh sách phim đã xem
        co_movies = list(set(co_movies) - set(user_watched_movies))

        # Lấy thông tin chi tiết của các phim được gợi ý
        co_movies_details = Movie.objects.filter(id__in=co_movies)
        return co_movies_details

    def matrix_factorization(self):
        # Thực hiện thuật toán matrix factorization từ dữ liệu trong bảng Myrating
        movie_ratings = Myrating.objects.values_list('user_id', 'movie_id', 'rating')
        num_users = User.objects.count()
        num_movies = Movie.objects.count()
        row = []
        col = []
        data = []

        for user_id, movie_id, rating in movie_ratings:
            row.append(user_id - 1)
            col.append(movie_id - 1)
            data.append(rating)

        user_ratings = coo_matrix((data, (row, col)), shape=(num_users, num_movies))

        # Sử dụng TruncatedSVD để học các embedding vector cho người dùng và phim
        svd = TruncatedSVD(n_components=min(num_users, num_movies) - 1)
        user_embedding = svd.fit_transform(user_ratings)
        movie_embedding = svd.components_.T

        return user_embedding, movie_embedding
    
    def get_matrix_factorization_recommendation(self, user_id, num_recommendations=18):
        user_embedding, movie_embedding = self.matrix_factorization()

        # Lấy embedding vector của người dùng
        user_vector = user_embedding[user_id - 1]

        # Tính điểm tương tự giữa embedding vector của người dùng và embedding vector của các phim
        similarity_scores = movie_embedding.dot(user_vector)

        # Sắp xếp các phim theo điểm tương tự giảm dần và lấy ra num_recommendations phim đề xuất
        recommended_movie_indices = similarity_scores.argsort()[::-1][:num_recommendations]

        # Lấy thông tin chi tiết của các phim được đề xuất
        recommended_movies = Movie.objects.filter(id__in=(recommended_movie_indices + 1))

        return recommended_movies
    
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