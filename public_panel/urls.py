from django.urls import path
from . import views
from public_panel.views import (
    home, register, forgetpassword,
    about_us, contact, bidnow, product_detail, login_view, showbid, logout_view, ProfileView, UserBiddingDetailsView,
    reset_password, user_dashboard
)

urlpatterns = [
    path('', home, name='home'),
    path('product_detail/<int:pk>/', product_detail, name='product_detail'),
    path('bidnow/', bidnow, name='bidnow'),

    # Homepage
    # path('home/', home, name='home'),  # Optional duplicate for /home
    
    # Authentication
    path('login/', login_view, name="login"),
    path('register/', register, name="register"),
    path('forgot-password/', forgetpassword, name='forgetpassword'),
    path('reset-password/<str:uidb64>/<str:token>/', reset_password, name='reset_password'),
    path('logout/', logout_view, name='logout'),

    # Static pages
    path('about/', about_us, name='about_us'),
    path('contact/', contact, name='contact'),

    # Product pages
    path('bidnow/', bidnow, name='bidnow'),
    path('showbid/', showbid, name='showbid'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('showbid', UserBiddingDetailsView.as_view(), name='showbid'),
    path('dashboard/', user_dashboard, name='user_dashboard'),

    #for search functionality
    path('search/', views.search, name='search'),

]
