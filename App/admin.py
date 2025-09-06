from django.contrib import admin
from App.models import Product, Brand, User, Customer, Bidnow, UserProfile, History, AboutUs, ContactUs, AuctionWinner, Feedback, SiteSetting

# Register your models here.
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'selling_price', 'discounted_price', 'event', 'is_upcoming', 'Auction']
    list_filter = ['category', 'brand', 'Auction', 'is_upcoming']
    search_fields = ['title', 'description']

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name']

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'user_type', 'is_staff']
    list_filter = ['user_type', 'is_staff', 'is_active']
    search_fields = ['username', 'email']

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'locality']
    search_fields = ['name', 'city']

@admin.register(Bidnow)
class BidnowAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'bid_amount', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'product__title']

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'created_at']
    search_fields = ['user__username']

@admin.register(History)
class HistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'history']
    search_fields = ['user__username', 'product__title']

@admin.register(AboutUs)
class AboutUsAdmin(admin.ModelAdmin):
    list_display = ['title', 'is_active', 'order', 'created_at']
    list_filter = ['is_active', 'order']
    search_fields = ['title']

@admin.register(ContactUs)
class ContactUsAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'email', 'subject']

@admin.register(AuctionWinner)
class AuctionWinnerAdmin(admin.ModelAdmin):
    list_display = ['product', 'winner', 'winning_bid', 'notified', 'won_at']
    list_filter = ['notified', 'won_at']
    search_fields = ['winner__username', 'product__title']

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    search_fields = ['name', 'email', 'subject']

@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    list_display = ['office_description', 'office_phone', 'office_email']
    search_fields = ['office_description']

