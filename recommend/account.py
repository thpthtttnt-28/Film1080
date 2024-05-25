from django.views import View
from django.views.generic import TemplateView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render

from .models import MyList
from django.contrib.auth.models import User
from .forms import SignUpForm, UserProfileForm
import os
from dotenv import load_dotenv
from django.contrib.auth import authenticate, login, logout


dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

class SignUp(FormView):
    template_name = 'recommend/signUp.html'
    form_class = SignUpForm
    success_url = '/profile/'

    def form_valid(self, form):
        user = form.save()
        login(self.request, user, backend='django.contrib.auth.backends.ModelBackend')
        return super().form_valid(form)

class Login(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'recommend/login.html')

    def post(self, request, *args, **kwargs):
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)

        if user is not None:
            if user.is_active:
                login(request, user)
                return redirect("home")
            else:
                return render(request, 'recommend/login.html', {'error_message': 'Your account is disabled'})
        else:
            return render(request, 'recommend/login.html', {'error_message': 'Invalid Login'})

class Logout(View):
    def get(self, request, *args, **kwargs):
        logout(request)
        return redirect("login")

class Profile(LoginRequiredMixin, TemplateView):
    template_name = 'recommend/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['user_profile'] = getattr(user, 'userprofile', None)
        context['user_full_name'] = user.get_full_name()
        return context

class ProfileEdit(LoginRequiredMixin, FormView):
    template_name = 'recommend/profile_edit.html'
    form_class = UserProfileForm
    success_url = '/profile/'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.request.user.userprofile
        return kwargs

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)

class UserList(View):
    def get(self, request, username, *args, **kwargs):
        user = get_object_or_404(User, username=username)
        movies = MyList.objects.filter(user=user).select_related('movie')
        return render(request, 'recommend/user_list.html', {'user': user, 'movies': movies})