from django.views.generic import TemplateView
from django.db.models import Q

from .models import Products
from .algo_rcm import SearchEngineRecommender, get_trending_products, RecentRecommender
import os
from dotenv import load_dotenv
from django.template.response import TemplateResponse

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

class HomeView(TemplateView):
    template_name = 'recommend/list.html'

    def get(self, request, *args, **kwargs):
        trending_products = get_trending_products()
        genre = request.GET.get('genre')
        query = request.GET.get('q')

        if query:
            products = Products.objects.filter(Q(title__icontains=query)).distinct()
            if products.exists():
                return self.search_products(request, products)

        if request.user.is_authenticated:
            recent_rcm = RecentRecommender(request.user)
            recent_products = recent_rcm.recommend(top_n=12)
            if genre:
                recent_products = [product for product in recent_products if product.genre == genre]

            context = {
                'trending_products': trending_products,
                'recent_products': recent_products,
            }
            return self.render_to_response(context)

        if genre:
            trending_products = trending_products.filter(genre=genre)

        context = {
            'trending_products': trending_products,
        }
        return self.render_to_response(context)

    def search_products(self, request, products):
        first_product_genre = products.first().genre
        recommender = SearchEngineRecommender()
        recommended_product_ids = recommender.recommend(first_product_genre, k=12)
        products_similar = Products.objects.filter(id__in=recommended_product_ids)

        return TemplateResponse(request, 'recommend/search_products.html', {
            'products': products,
            'products_similar': products_similar
        })
