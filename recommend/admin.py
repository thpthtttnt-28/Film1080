from django.contrib import admin
from .models import Movie, Myrating, MyList, UserProfile, Comment, Report

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'address', 'phone_number', 'is_vip')
    list_filter = ('is_vip',)
    search_fields = ('user__username', 'name', 'address', 'phone_number')

admin.site.register(UserProfile, UserProfileAdmin)

class MovieAdmin(admin.ModelAdmin):
    list_display = ('title', 'overview', 'genre', 'year', 'is_vip')
    search_fields = ['title']  # Tìm kiếm theo trường 'title'

admin.site.register(Movie, MovieAdmin)

class MyratingAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'movie_id', 'rating')

    def user_id(self, obj):
        return obj.user.id

    def movie_id(self, obj):
        return obj.movie.id

admin.site.register(Myrating, MyratingAdmin)

class MyListAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'movie_id', 'watch')

    def user_id(self, obj):
        return obj.user.id

    def movie_id(self, obj):
        return obj.movie.id

admin.site.register(MyList, MyListAdmin)

class CommentAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'movie_id', 'text', 'created_at')

    def user_id(self, obj):
        return obj.user.id

    def movie_id(self, obj):
        return obj.movie.id

admin.site.register(Comment, CommentAdmin)

admin.site.register(Report)
