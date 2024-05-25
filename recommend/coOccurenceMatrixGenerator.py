import os

os.environ['PYSPARK_PYTHON'] = 'F:\\test\\python.exe'
os.environ['PYSPARK_DRIVER_PYTHON'] = 'F:\\test\\python.exe'

import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql.functions import collect_list, col, udf
from pyspark.sql.types import ArrayType, StringType
from pyspark.ml.feature import CountVectorizer
import joblib
from django.core.cache import cache

class CoOccurrenceMatrixGenerator:
    def __init__(self, joblib_file='co_occurence_matrix/co_occurrence_matrix.pkl'):
        self.joblib_file = joblib_file
        self.spark = SparkSession.builder.appName("CoOccurrenceMatrix").getOrCreate()

    def get_or_create_matrix(self):
        co_occurrence_dict = cache.get('co_occurrence_dict')
        if not co_occurrence_dict:
            co_occurrence_dict = self._load_matrix()
            cache.set('co_occurrence_dict', co_occurrence_dict, timeout=None)
        return co_occurrence_dict
    
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
        user_products = self._group_by_user(spark_df)
        user_products = self._convert_products_to_string(user_products)
        co_occurrence_matrix = self._create_co_occurrence_matrix(user_products)
        co_occurrence_dict = self._convert_to_dict(co_occurrence_matrix)
        self._save_matrix(co_occurrence_dict)
        return co_occurrence_dict

    def _get_queryset(self):
        from .models import WatchHistory
        return WatchHistory.objects.filter(watch=True).values('user_id', 'product_id')

    def _create_dataframe(self, queryset):
        return pd.DataFrame(list(queryset))

    def _create_spark_dataframe(self, df):
        return self.spark.createDataFrame(df)

    def _group_by_user(self, spark_df):
        return spark_df.groupBy("user_id").agg(collect_list("product_id").alias("products"))

    def _convert_products_to_string(self, user_products):
        convert_to_string_udf = udf(lambda product_ids: [str(product_id) for product_id in product_ids], ArrayType(StringType()))
        return user_products.withColumn("products", convert_to_string_udf(col("products")))

    def _create_co_occurrence_matrix(self, user_products):
        cv = CountVectorizer(inputCol="products", outputCol="features", binary=True)
        model = cv.fit(user_products)
        result = model.transform(user_products)
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
