import os

os.environ['PYSPARK_PYTHON'] = 'F:\\test\\python.exe'
os.environ['PYSPARK_DRIVER_PYTHON'] = 'F:\\test\\python.exe'

import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql.functions import collect_list, col, udf
from pyspark.sql.types import ArrayType, StringType
from pyspark.ml.feature import CountVectorizer
import joblib

class CoOccurrenceMatrixGenerator:
    def __init__(self, joblib_file='co_occurence_matrix/co_occurrence_matrix.pkl'):
        self.joblib_file = joblib_file
        self.spark = SparkSession.builder.appName("CoOccurrenceMatrix").getOrCreate()

    def get_or_create_matrix(self):
        return self._load_matrix()
    
    def _load_matrix(self):
        try:
            co_occurrence_dict = joblib.load(self.joblib_file)
            print(f"Co-Occurrence Matrix loaded from {self.joblib_file}")
            return co_occurrence_dict
        except FileNotFoundError:
            return self._train_and_save_matrix()

    def _train_and_save_matrix(self):
        print("Training Co-Occurrence Matrix...")
        queryset = self._get_queryset()
        df = self._create_dataframe(queryset)
        spark_df = self._create_spark_dataframe(df)
        user_movies = self._group_by_user(spark_df)
        user_movies = self._convert_movies_to_string(user_movies)
        co_occurrence_matrix = self._create_co_occurrence_matrix(user_movies)
        co_occurrence_dict = self._convert_to_dict(co_occurrence_matrix)
        self._save_matrix(co_occurrence_dict)
        return co_occurrence_dict

    def _get_queryset(self):
        from .models import MyList
        return MyList.objects.filter(watch=True).values('user_id', 'movie_id')

    def _create_dataframe(self, queryset):
        return pd.DataFrame(list(queryset))

    def _create_spark_dataframe(self, df):
        return self.spark.createDataFrame(df)

    def _group_by_user(self, spark_df):
        return spark_df.groupBy("user_id").agg(collect_list("movie_id").alias("movies"))

    def _convert_movies_to_string(self, user_movies):
        convert_to_string_udf = udf(lambda movie_ids: [str(movie_id) for movie_id in movie_ids], ArrayType(StringType()))
        return user_movies.withColumn("movies", convert_to_string_udf(col("movies")))

    def _create_co_occurrence_matrix(self, user_movies):
        cv = CountVectorizer(inputCol="movies", outputCol="features", binary=True)
        model = cv.fit(user_movies)
        result = model.transform(user_movies)
        return result.select("features").rdd \
            .map(lambda row: row["features"].toArray()) \
            .flatMap(lambda x: [(i, j) for i in x for j in x]) \
            .filter(lambda x: x[0] != x[1]) \
            .map(lambda x: ((x[0], x[1]), 1)) \
            .reduceByKey(lambda x, y: x + y) \
            .collect()

    def _convert_to_dict(self, co_occurrence_matrix):
        co_occurrence_dict = {}
        for ((i, j), count) in co_occurrence_matrix:
            if i not in co_occurrence_dict:
                co_occurrence_dict[i] = {}
            co_occurrence_dict[i][j] = count
        return co_occurrence_dict

    def _save_matrix(self, co_occurrence_dict):
        joblib.dump(co_occurrence_dict, self.joblib_file)
        print(f"Co-Occurrence Matrix saved to {self.joblib_file}")
