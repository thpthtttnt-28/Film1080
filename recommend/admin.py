from django.contrib import admin
from .models import Movie, Myrating, MyList, UserProfile,Comment, Report

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'address', 'phone_number', 'is_vip')
    list_filter = ('is_vip',)
    search_fields = ('user__username', 'name', 'address', 'phone_number')

admin.site.register(Movie)
admin.site.register(Myrating)
admin.site.register(MyList)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(Comment)
admin.site.register(Report)