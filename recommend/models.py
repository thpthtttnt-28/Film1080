from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.contrib.auth.models import User
from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.models.signals import post_save


# Create your models here.

class Movie(models.Model):
    title = models.CharField(max_length=200)
    overview = models.TextField()
    movie_logo = models.FileField()
    genre = models.CharField(max_length=200)
    year = models.IntegerField()
    is_vip = models.BooleanField(default=False)

    def __str__(self):
        return self.title

class Myrating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    rating = models.IntegerField(default=0, validators=[MaxValueValidator(5), MinValueValidator(0)])

    def __str__(self):
        return f'{self.user} rated {self.movie} {self.rating}'

class MyList(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    watch = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.user} added {self.movie} to list'
        
class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Comment by {self.user} on {self.movie}'
    
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, unique=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    address = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    is_vip = models.BooleanField(default=False)
    banned = models.BooleanField(default=False)

    def __str__(self):
        return self.name or self.user.username
    
@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        try:
            instance.userprofile.save()
        except UserProfile.DoesNotExist:
            UserProfile.objects.create(user=instance)

class Report(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.ForeignKey('Comment', on_delete=models.CASCADE)
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Report by {self.user.username} on {self.comment.id}'
    
class CachedModel(models.Model):
    model_state = models.BinaryField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.created_at)