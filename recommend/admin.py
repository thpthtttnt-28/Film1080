from django.contrib import admin
from .models import Products, ProductRating, WatchHistory, UserProfile, Comment, Report, ProductType

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_vip', 'banned')
    list_filter = ('is_vip',)
    search_fields = ['user__username']

admin.site.register(UserProfile, UserProfileAdmin)

class productAdmin(admin.ModelAdmin):
    list_display = ('title', 'overview', 'genre', 'year', 'is_vip')
    search_fields = ['title']  # Tìm kiếm theo trường 'title'

admin.site.register(Products, productAdmin)

class MyratingAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'product_id', 'rating')

    def user_id(self, obj):
        return obj.user.id

    def product_id(self, obj):
        return obj.product.id

admin.site.register(ProductRating, MyratingAdmin)

class MyListAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'product_id', 'watch')

    def user_id(self, obj):
        return obj.user.id

    def product_id(self, obj):
        return obj.product.id

admin.site.register(WatchHistory, MyListAdmin)

class CommentAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'product_id', 'text', 'created_at')

    def user_id(self, obj):
        return obj.user.id

    def product_id(self, obj):
        return obj.product.id

admin.site.register(Comment, CommentAdmin)

admin.site.register(Report)
admin.site.register(ProductType)