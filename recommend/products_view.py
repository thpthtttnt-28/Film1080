from django.views import View
from django.views.generic import DetailView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.contrib import messages
from django.http import HttpResponseRedirect, Http404
from django.core.paginator import Paginator
from django.db.models import Q, Avg
from .models import Products, ProductRating, WatchHistory, Comment, Report

class productDetailView(LoginRequiredMixin, DetailView):
    model = Products
    template_name = 'recommend/detail.html'
    context_object_name = 'product'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product_id = self.kwargs['pk']
        product = self.get_object()
        user = self.request.user

        if not user.userprofile.is_vip and product.is_vip:
            raise Http404("Only VIP members can access this product.")

        try:
            watch_item = WatchHistory.objects.get(product_id=product_id, user=user)
            context['update'] = watch_item.watch
        except WatchHistory.DoesNotExist:
            context['update'] = False

        user_rating = ProductRating.objects.filter(product_id=product_id, user=user).first()
        context['product_rating'] = user_rating.rating if user_rating else 0
        context['rate_flag'] = user_rating is not None

        context['comments'] = Comment.objects.filter(product=product).order_by('-created_at')
        context['product_avg_rating'] = ProductRating.objects.filter(product_id=product_id).aggregate(Avg('rating'))['rating__avg'] or 0

        return context

    def post(self, request, *args, **kwargs):
        product = self.get_object()
        user = request.user

        if 'watch' in request.POST:
            watch_flag = request.POST['watch']
            update = watch_flag == 'on'
            mylist, created = WatchHistory.objects.get_or_create(product_id=product.id, user=user)
            mylist.watch = update
            mylist.save()
            messages.success(request, "product added to your list!" if update else "product removed from your list!")

        elif 'rating' in request.POST:
            rate = request.POST['rating']
            rating, created = ProductRating.objects.get_or_create(product_id=product.id, user=user)
            rating.rating = rate
            rating.save()
            messages.success(request, "Rating has been submitted!")

        elif 'comment' in request.POST:
            comment_text = request.POST['comment']
            Comment.objects.create(user=user, product=product, text=comment_text)
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
    context_object_name = 'products'

    def get_queryset(self):
        user = self.request.user
        query = self.request.GET.get('q')
        watch_history = WatchHistory.objects.filter(user=user, watch=True).select_related('product')

        products = [watch.product for watch in watch_history]

        if query:
            products = products.filter(Q(title__icontains=query)).distinct()

        return products

class productFilterView(View):
    def get(self, request, *args, **kwargs):
        genre = request.GET.get('genre')
        products = Products.objects.all()

        if genre:
            products = products.filter(genre__icontains=genre)

        paginator = Paginator(products, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = {
            'products': page_obj,
        }

        return render(request, 'recommend/product_filter.html', context)