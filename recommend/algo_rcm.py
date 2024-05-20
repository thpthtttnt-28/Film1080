# To get similar movies based on user rating
def get_similar(movie_name,rating,corrMatrix):
    similar_ratings = corrMatrix[movie_name]*(rating-2.5)
    similar_ratings = similar_ratings.sort_values(ascending=False)
    return similar_ratings

import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.neighbors import NearestNeighbors
from .models import Movie

class ContentBasedRecommender:
    def __init__(self):
        self.movies_df = pd.DataFrame(list(Movie.objects.all().values('id', 'title', 'genre')))
        self.model = None
        self.vectorizer = CountVectorizer()

    def train_model(self):
        # Transform the genre into a count matrix
        count_matrix = self.vectorizer.fit_transform(self.movies_df['genre'])
        # Train kNN model
        self.model = NearestNeighbors(metric='cosine', algorithm='brute')
        self.model.fit(count_matrix)
        
    def recommend(self, query, k=5):
        if self.model is None:
            self.train_model()

        # Transform the query genre
        query_vector = self.vectorizer.transform([query])
        distances, indices = self.model.kneighbors(query_vector, n_neighbors=k)

        # Get recommended movie ids
        recommended_movie_ids = self.movies_df.iloc[indices[0]]['id'].tolist()
        return recommended_movie_ids
