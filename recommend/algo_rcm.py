import os
import numpy as np
import pandas as pd
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD
from scipy.sparse import coo_matrix
from .models import Products, WatchHistory, ProductRating, User
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
from django.db.models import Q, Avg, Count, Case, When
from .coOccurenceMatrixGenerator import CoOccurrenceMatrixGenerator
from .models import CachedModel
import pickle

class SearchEngineRecommender:
    def __init__(self):
        self.products_df = pd.DataFrame(list(Products.objects.all().values('id', 'title', 'genre')))
        self.model = None
        self.mlb = MultiLabelBinarizer()

    def preprocess_genres(self):
        if not isinstance(self.products_df['genre'][0], list):
            # Tách các thể loại cách nhau bằng dấu phẩy
            self.products_df['genre'] = self.products_df['genre'].apply(lambda x: x.split(', '))

        self.genre_matrix = self.mlb.fit_transform(self.products_df['genre'])


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
        
    def recommend(self, genre, k=1):
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

        # Get recommended product ids
        recommended_product_ids = self.products_df.iloc[indices[0]]['id'].tolist()

        return recommended_product_ids[1:]

class RecentRecommender:
    def __init__(self, user):
        self.user = user
        self.co_matrix_generator = CoOccurrenceMatrixGenerator()
        self.co_occurrence_matrix = self.co_matrix_generator.get_or_create_matrix()
        self.model = None
        self.mlb = MultiLabelBinarizer()
        self.products_df = pd.DataFrame(list(Products.objects.all().values('id', 'title', 'genre')))
        if self.model is None:
            self.load_cached_knn_model()

    def preprocess_genres(self):
        self.products_df['genre'] = self.products_df['genre'].apply(lambda x: x.split(', '))
        self.genre_matrix = self.mlb.fit_transform(self.products_df['genre'])

    def load_cached_knn_model(self):
        cached_model = CachedModel.objects.last()
        if cached_model:
            self.preprocess_genres()
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
        watched_products = self._get_watched_products()
        if not watched_products:
            return self._get_popular_products(top_n)
        watched_products = watched_products[:10] if len(watched_products) > 10 else watched_products
        combined_recommendations = self._combine_recommendations(
            self._generate_co_occurrence_recommendations(watched_products),
            self._generate_knn_recommendations(watched_products, top_n)
        )
        return self._get_top_n_recommendations(combined_recommendations, top_n)

    def _get_watched_products(self):
        return list(WatchHistory.objects.filter(user=self.user, watch=True).values_list('product_id', flat=True))

    def _generate_co_occurrence_recommendations(self, watched_products):
        recommendations = {}
        for product in watched_products:
            if product in self.co_occurrence_matrix:
                for co_product, score in self.co_occurrence_matrix[product].items():
                    if co_product not in watched_products:
                        recommendations[co_product] = recommendations.get(co_product, 0) + score
        return recommendations

    def _generate_knn_recommendations(self, watched_products, top_n):
        recommendations = []
        for product_id in watched_products:
            product = Products.objects.get(id=product_id)
            genre_list = product.genre.split(', ')
            genre_vector = self.mlb.transform([genre_list])
            _, indices = self.model.kneighbors(genre_vector, n_neighbors=top_n + 1)
            recommendations.extend(self.products_df.iloc[indices[0]]['id'].tolist()[1:])
        return recommendations

    def _combine_recommendations(self, co_occurrence_recommendations, knn_recommendations):
        for product in knn_recommendations:
            co_occurrence_recommendations[product] = co_occurrence_recommendations.get(product, 0) + 1
        return co_occurrence_recommendations

    def _get_top_n_recommendations(self, recommendations, top_n):
        sorted_recommendations = sorted(recommendations.items(), key=lambda item: item[1], reverse=True)
        top_product_ids = [product_id for product_id, _ in sorted_recommendations[:top_n]]
        return Products.objects.filter(id__in=top_product_ids)

    def _get_popular_products(self, top_n):
        trending_product_ids = WatchHistory.objects.values('product').annotate(total_watch=Count('product')).order_by('-total_watch')[:12]
        return Products.objects.filter(id__in=[product['product'] for product in trending_product_ids])
    
# To get similar products based on user rating
def get_similar(product_name,rating,corrMatrix):
    similar_ratings = corrMatrix[product_name]*(rating-2.5)
    similar_ratings = similar_ratings.sort_values(ascending=False)
    return similar_ratings

def get_trending_products():
    # Gợi ý phim theo số lượt xem trong bảng MyList
    trending_product_ids = WatchHistory.objects.values('product').annotate(total_watch=Count('product')).order_by('-total_watch')[:12]
    trending_products = Products.objects.filter(id__in=[product['product'] for product in trending_product_ids])
    return trending_products