from django.contrib.auth import get_user_model
from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.utils import timezone  

# Custom User model
class User(AbstractUser):
    USER_TYPES = (
        ('admin', 'Admin'),
        ('user', 'User'),
    )

    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    user_type = models.CharField(max_length=10, choices=USER_TYPES, default='user')

    def __str__(self):
        return self.username

# Customer model linked to custom User
class Customer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    locality = models.CharField(max_length=200)
    city = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.name} - {self.city}"

CATEGORY_CHOICES = (
    ('M', 'Mobile'),
    ('L', 'Laptop'),
    ('W', 'Watch'),
)

class Brand(models.Model):
    name = models.CharField(max_length=20)

    def __str__(self):
        return self.name

class Product(models.Model):
    title = models.CharField(max_length=50)
    selling_price = models.PositiveIntegerField()
    discounted_price = models.PositiveIntegerField()
    event = models.DateTimeField(default=timezone.now)
    event_ends = models.DateTimeField(null=True, blank=True)
    description = models.TextField()
    brand = models.CharField(max_length=100, null=True, blank=True)
    brands = models.ForeignKey(Brand, on_delete=models.CASCADE, null=True, blank=True)
    category = models.CharField(choices=CATEGORY_CHOICES, max_length=1)
    product_image = models.ImageField(upload_to='productimg/')
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE, null=True, blank=True)
    user_email = models.EmailField(max_length=100, default='', blank=True)
    is_upcoming = models.BooleanField(default=True)
    Auction = models.BooleanField(default=False)
    is_winner_notified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title}"

class Bidnow(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bidnow')
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    bid_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(default=timezone.now) 
    class Meta:
        # This ensures the newest bids always appear at the top
        ordering = ['-created_at']
        # This helps the Django Admin display the name correctly
        verbose_name = "Bid"
        verbose_name_plural = "Bids"
    def __str__(self):
        return f"{self.user} - {self.product} - Rs. {self.bid_amount}"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=12)
    # add more fields as needed
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.user.username


class History(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)    
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    history = models.PositiveIntegerField(default=0)    
    def __str__(self):
        return str(self.id)
    
class AboutUs(models.Model):
    image = models.ImageField(upload_to='about_us/')
    title = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "About Us"
        verbose_name_plural = "About Us"
        ordering = ['order', '-created_at']

class ContactUs(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.subject}"

    class Meta:
        verbose_name = "Contact Us"
        verbose_name_plural = "Contact Us"

class AuctionWinner(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE)
    winner = models.ForeignKey(User, on_delete=models.CASCADE)
    winning_bid = models.DecimalField(max_digits=10, decimal_places=2)
    notified = models.BooleanField(default=False)
    won_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.winner.username} won {self.product.title} with Rs. {self.winning_bid}"

class Feedback(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} - {self.subject}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Feedback'
        verbose_name_plural = 'Feedbacks'

class SiteSetting(models.Model):
    office_description = models.CharField(max_length=255)
    office_phone = models.IntegerField()
    office_address = models.CharField(max_length=100)
    office_email = models.EmailField()
    facebook = models.URLField(blank=True, null=True)
    x = models.URLField(blank=True, null=True)
    instagram = models.URLField(blank=True, null=True)
    linkedin = models.URLField(blank=True, null=True)
    iframe = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.office_description

# Fraud Detection Models
class UserBehaviorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='behavior_profile')
    risk_score = models.FloatField(default=0.0, help_text="Risk score from 0-100")
    total_bids = models.PositiveIntegerField(default=0)
    successful_bids = models.PositiveIntegerField(default=0)
    average_bid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    last_bid_time = models.DateTimeField(null=True, blank=True)
    suspicious_activity_count = models.PositiveIntegerField(default=0)
    account_age_days = models.PositiveIntegerField(default=0)
    is_flagged = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - Risk: {self.risk_score}"

class BidValidation(models.Model):
    VALIDATION_TYPES = (
        ('VELOCITY', 'Bid Velocity Check'),
        ('AMOUNT', 'Bid Amount Validation'),
        ('PATTERN', 'Suspicious Pattern'),
        ('BEHAVIOR', 'User Behavior Analysis'),
        ('IP', 'IP Address Check'),
        ('DEVICE', 'Device Fingerprint'),
    )
    
    bid = models.ForeignKey(Bidnow, on_delete=models.CASCADE, related_name='validations')
    validation_type = models.CharField(max_length=20, choices=VALIDATION_TYPES)
    is_valid = models.BooleanField(default=True)
    risk_score = models.FloatField(default=0.0)
    details = models.JSONField(default=dict, help_text="Additional validation details")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.bid.user.username} - {self.validation_type} - {'Valid' if self.is_valid else 'Invalid'}"

class FraudAlert(models.Model):
    ALERT_TYPES = (
        ('HIGH_RISK_BID', 'High Risk Bid'),
        ('SUSPICIOUS_PATTERN', 'Suspicious Bidding Pattern'),
        ('VELOCITY_ABUSE', 'Bid Velocity Abuse'),
        ('AMOUNT_ANOMALY', 'Bid Amount Anomaly'),
        ('MULTIPLE_ACCOUNTS', 'Multiple Account Usage'),
        ('AUTO_BIDDING', 'Automated Bidding Detected'),
    )
    
    SEVERITY_LEVELS = (
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    bid = models.ForeignKey(Bidnow, on_delete=models.CASCADE, null=True, blank=True)
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS)
    description = models.TextField()
    risk_score = models.FloatField()
    is_resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_alerts')
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.alert_type} - {self.user.username} - {self.severity}"

class BidIncrement(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    current_bid = models.DecimalField(max_digits=10, decimal_places=2)
    next_minimum_bid = models.DecimalField(max_digits=10, decimal_places=2)
    increment_amount = models.DecimalField(max_digits=10, decimal_places=2)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.title} - Min: {self.next_minimum_bid}"

class AutoBid(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    max_bid_amount = models.DecimalField(max_digits=10, decimal_places=2)
    current_bid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.product.title} - Max: {self.max_bid_amount}"
    
# for searching algorithms
User = get_user_model()

class Auction(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    starting_price = models.DecimalField(max_digits=10, decimal_places=2)
    # seller = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title
