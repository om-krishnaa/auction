from django.shortcuts import render, redirect,get_object_or_404
from django.views import View
from App.models import Product,Bidnow,ContactUs,AuctionWinner,AboutUs,User
from admin_panel.form import BidForm
from django.contrib.auth import authenticate, login as auth_login,logout
from datetime import datetime, timedelta
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.timezone import now
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from App.models import SiteSetting
from admin_panel.form import SiteSettingForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import random
import re
from django.db.models import Q
from .models import AuctionItem
from django.core.cache import cache
from django.conf import settings
import logging
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str

# Configure logger
logger = logging.getLogger(__name__)

def home(request):
    auction = Product.objects.filter(Auction=True)
    upcoming = Product.objects.filter(is_upcoming=True)
    return render(request, 'public_panel/index.html', {
        'Auction': auction,
        'upcoming': upcoming
    })

@login_required(login_url='/login/')
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    current_highest = Bidnow.objects.filter(product=product).order_by('-bid_amount').first()
    return render(request, 'public_panel/product_detail.html', {
        'product': product,
        'current_highest': current_highest.bid_amount if current_highest else 0,
    })


def showbid(request):
    bids = Bidnow.objects.filter(user=request.user)
    return render(request, 'public_panel/showbid.html', {'bids': bids})

def bidnow(request):
    # Get the product id from the POST data
    prod_id = request.POST.get('prod_id')
    product = get_object_or_404(Product, id=prod_id)

    # Check if the user has already placed a bid for this product
    already_bid = Bidnow.objects.filter(user=request.user, product=product).exists()

    if request.method == 'POST':
        form = BidForm(request.POST)

        # If the form is valid and the user hasn't placed a bid
        if form.is_valid() and not already_bid:
            bid_amount = form.cleaned_data['bid_amount']

            # Use advanced bidding service with fraud detection
            from App.bidding_service import bidding_service
            
            # Get client IP and user agent for fraud detection
            ip_address = request.META.get('REMOTE_ADDR', '')
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            # Place bid with fraud detection
            result = bidding_service.place_bid(
                user=request.user,
                product=product,
                bid_amount=bid_amount,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            if result['success']:
                messages.success(request, f"Your bid of Rs. {bid_amount} has been placed successfully!")
                
                # Show warnings if any
                if result.get('warnings'):
                    for warning in result['warnings']:
                        messages.warning(request, warning)
                
                # Show risk score if high
                if result.get('risk_score', 0) > 60:
                    messages.info(request, f"Note: Your bid has a risk score of {result['risk_score']:.1f}%")
            else:
                messages.error(request, result.get('message', 'Failed to place bid'))
                if result.get('details'):
                    for detail in result['details']:
                        messages.error(request, detail)
            
            return render(request, 'public_panel/bidnow.html', {'fm': form, 'product': product, 'already_bid': already_bid})

        # If the user has already placed a bid
        elif already_bid:
            messages.error(request, "You have already placed a bid for this product.")
            return render(request, 'public_panel/bidnow.html', {'fm': form, 'product': product, 'already_bid': already_bid})
        else:
            form = BidForm()  # Initialize empty form

    # Get current bid information
    from App.bidding_service import bidding_service
    bid_info = bidding_service.get_current_bid_info(product)
    
    # Context for rendering
    return render(request, 'public_panel/bidnow.html', {
        'fm': form,
        'product': product,
        'already_bid': already_bid,
        'bid_info': bid_info
    })


# from django.core.mail import send_mail
# from django.contrib.auth import get_user_model

# User = get_user_model()

# class ProductDetailView(View):
#     def get(self, request, pk):
#         if not request.user.is_authenticated:
#             return redirect('/account/login/')

#         product = get_object_or_404(Product, pk=pk)
#         fm = BidForm()
#         t1 = product.event_ends
#         t2 = now()
#         t3 = t1 - t2

#         # 🟨 If auction has ended
#         if t3.total_seconds() <= 0:
#             remaining_time = 'Ended'

#             # ✅ If auction just ended and winner is not yet notified
#             if product.Auction and not product.is_winner_notified:
#                 highest_bid = Bidnow.objects.filter(product=product).order_by('-amount').first()
#                 if highest_bid:
#                     user = highest_bid.user
                    
#                     try:
#                         send_mail(
#                             subject = '🎉 Congratulations! You Won the Auction',
#                             message = (
#                             f"Dear {user.username},\n\n"
#                             f"You have won the auction for \"{product.product_name}\" with a bid of ${highest_bid.amount}.\n"
#                             f"Please log in to your account to proceed.\n\n"
#                             f"Thank you for using E-Auction!"),
#                             from_email = settings.EMAIL_HOST_USER,
#                             recipient_list=[user.email],                         
#                             fail_silently=False,   
#                             html_message="hello" 
#                         )
#                         product.is_winner_notified = True
#                         product.save()
#                         print("✅ Winner email sent.")
#                     except Exception as e:
#                         print(f"❌ Failed to send email: {e}")

#             return render(request, 'admin_panel/productdetail.html', {
#                 'product': product,
#                 'remaining_time': remaining_time,
#                 'timeNow': t2,
#                 'time': 'time'
#             })

#         # 🟩 If auction still active
#         return render(request, 'admin_panel/productdetail.html', {
#             'product': product,
#             'remaining_time': t3,
#             'timeNow': t2,
#             'fm': fm
#         })

#     def post(self, request, pk):
#         product = get_object_or_404(Product, pk=pk)
#         a = BidForm(request.POST)
#         if a.is_valid():
#             bid = a.save(commit=False)
#             bid.product = product
#             bid.user = request.user
#             bid.save()
#         return redirect(request.path)

from django.utils import timezone
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class ProductDetailView(View):
    def get(self, request, pk):
        if not request.user.is_authenticated:
            return redirect('/account/login/')

        product = get_object_or_404(Product, pk=pk)
        now_time = timezone.now()
        time_left = product.event_ends - now_time

        if time_left.total_seconds() <= 0:
            remaining_time = 'Ended'

            if product.Auction and not product.is_winner_notified:
                highest_bid = Bidnow.objects.filter(product=product).order_by('-amount').first()
                if highest_bid:
                    user = highest_bid.user
                    try:
                        send_mail(
                            subject='🎉 Congratulations! You Won the Auction',
                            message=(
                                f"Dear {user.username},\n\n"
                                f"You have won the auction for \"{product.product_name}\" with a bid of ${highest_bid.amount}.\n"
                                f"Please log in to your account to proceed.\n\n"
                                f"Thank you for using E-Auction!"
                            ),
                            from_email=settings.EMAIL_HOST_USER,
                            recipient_list=[user.email],
                            fail_silently=False,
                        )
                        product.is_winner_notified = True
                        product.save()
                        logger.info("✅ Winner email sent.")
                    except Exception as e:
                        logger.error(f"❌ Failed to send email: {e}")

            return render(request, 'admin_panel/productdetail.html', {
                'product': product,
                'remaining_time': remaining_time,
                'timeNow': now_time,
            })

        return render(request, 'admin_panel/productdetail.html', {
            'product': product,
            'remaining_time': time_left,
            'timeNow': now_time,
            'fm': BidForm()
        })

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        if product.event_ends <= timezone.now():
            # Optional: use Django messages framework
            return redirect(request.path)

        form = BidForm(request.POST)
        if form.is_valid():
            bid = form.save(commit=False)
            bid.product = product
            bid.user = request.user
            bid.save()
        return redirect(request.path)



# class ProductDetailView(View):
#     def get(self, request, pk):
#         if request.user.is_authenticated:
#             product = Product.objects.get(pk=pk)
#             fm = BidForm()
#             t1 = product.event_ends
#             t2 = now()  # Use timezone-aware datetime
#             t3 = t1 - t2

#             if t3.total_seconds() <= 0:
#                 remaining_time = 'Ended'
#                 return render(request, 'admin_panel/productdetail.html', {
#                     'product': product,
#                     'remaining_time': remaining_time,
#                     'timeNow': t2,
#                     'time': 'time'
#                 })

#             return render(request, 'admin_panel/productdetail.html', {
#                 'product': product,
#                 'remaining_time': t3,
#                 'timeNow': t2,
#                 'fm': fm
#             })
#         else:
#             return redirect('/account/login/')

#     def post(self, request):
#         a = BidForm(request.POST)
#         if a.is_valid():
#             a.save()
#         return redirect(request.path)  

    

# class ProductDetailView(View):
#     def get(self,request,pk):
#         if request.user.is_authenticated:
#             product = Product.objects.get(pk=pk)
#             fm = BidForm()
#             t1 = product.event_ends
#             t2 = datetime.now()
#             t3 = t1-t2
#             if (t3.days < 0 ):
#                 remaining_time = 'Ended'
#                 return render(request,'admin_panel/productdetail.html',{'product':product,'remaining_time':remaining_time,'timeNow':t2,'time':'time'})
    

#         else:
#             return redirect('/account/login/')
#     def post(self,request):
#         a = BidForm(request.POST)
#         if a.is_valid():
#             a.save()


def logout_view(request):
    logout(request)
    return redirect('login')
# def home(request):
#     return render(request, 'public_panel/index.html')


# login 

User = get_user_model()

def login_view(request):
    # If already logged in, redirect accordingly
    if request.user.is_authenticated:
        if request.user.user_type == 'admin':
            return redirect('admin')  # Redirect to admin panel
        return redirect('home')  # Regular user dashboard

    if request.method == "POST":
        username_or_email = request.POST.get('username')
        password = request.POST.get('password')

        if not username_or_email or not password:
            messages.error(request, "Please fill in both fields.")
            return redirect('login')

        try:
            # Identify by email or username
            if '@' in username_or_email:
                user_obj = User.objects.get(email=username_or_email)
                username = user_obj.username  # Get the actual username
            else:
                username = username_or_email

            # Authenticate using username
            user = authenticate(request, username=username, password=password)

            if user is not None:
                if user.is_active:
                    if user.user_type == 'admin':
                        messages.error(request, "Admin users should use the admin login page.")
                        return redirect('login')
                    else:
                        auth_login(request, user)
                        messages.success(request, f"Welcome back, {user.username}!")
                        return redirect('home')
                else:
                    messages.error(request, "Your account is not active. Please contact support.")
            else:
                messages.error(request, "Invalid username/email or password.")
                logger.error(f"Failed login attempt for username: {username}")
        except User.DoesNotExist:
            messages.error(request, "No account found with this username/email.")
            logger.error(f"Login attempt with non-existent user: {username_or_email}")
        except Exception as e:
            messages.error(request, "An error occurred during login. Please try again.")
            logger.error(f"Login error: {str(e)}")

    # Add CSRF token to context for debugging
    from django.middleware.csrf import get_token
    csrf_token = get_token(request)
    logger.info(f"CSRF Token generated: {csrf_token}")
    
    return render(request, 'public_panel/login.html')


# registrstion

from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import random

# OTP generation function removed - no longer needed for simple registration

def validate_password(password):
    """
    Validate password strength
    Returns (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one number"
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character"
    return True, ""

def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Basic validation
        if not all([username, email, password]):
            messages.error(request, "All fields are required.")
            return render(request, 'public_panel/register.html')

        # Check if user already exists
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return render(request, 'public_panel/register.html')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return render(request, 'public_panel/register.html')

        # Validate password strength
        is_valid_password, password_error = validate_password(password)
        if not is_valid_password:
            messages.error(request, password_error)
            return render(request, 'public_panel/register.html')

        # Validate email
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "Invalid email address. Please enter a valid email.")
            return render(request, 'public_panel/register.html')

        # Create user directly without email verification
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                user_type='user'
            )
            
            # Create user behavior profile
            from App.models import UserBehaviorProfile
            UserBehaviorProfile.objects.create(
                user=user,
                risk_score=0.0,
                account_age_days=0
            )
            
            messages.success(request, "Registration successful! You can now login.")
            return redirect('login')
            
        except Exception as e:
            messages.error(request, f"Error creating account: {str(e)}")
            return render(request, 'public_panel/register.html')

    return render(request, 'public_panel/register.html')

# OTP verification functions removed - no longer needed for simple registration





# forget password
from django.conf import settings
from django.utils.crypto import get_random_string

User = get_user_model()

def forgetpassword(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            
            # Generate password reset token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Build password reset link
            reset_link = request.build_absolute_uri(
                f'/reset-password/{uid}/{token}/'
            )
            
            # Email content
            html_message = f'''
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 10px; background-color: #f9f9f9;">
                    <div style="text-align: center; margin-bottom: 20px;">
                        <h2 style="color: #0d6efd;">Password Reset Request</h2>
                    </div>
                    <div style="background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <p>Hello {user.username},</p>
                        <p>We received a request to reset your password. Click the button below to create a new password:</p>
                        <div style="text-align: center; margin: 20px 0;">
                            <a href="{reset_link}" style="background-color: #0d6efd; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">Reset Password</a>
                        </div>
                        <p>If you didn't request this, you can safely ignore this email. The link will expire in 24 hours.</p>
                        <hr style="border-top: 1px solid #eee; margin: 20px 0;">
                        <p style="color: #666; font-size: 12px; text-align: center;">
                            This is an automated message, please do not reply.
                        </p>
                    </div>
                </div>
            '''
            
            try:
                # Send password reset email
                send_mail(
                    subject="Reset Your Password - eAuction",
                    message=f"Click the following link to reset your password: {reset_link}",
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[email],
                    fail_silently=False,
                    html_message=html_message
                )
                messages.success(request, "Password reset link has been sent to your email.")
                logger.info(f"Password reset email sent to {email}")
            except Exception as e:
                logger.error(f"Failed to send password reset email: {str(e)}")
                messages.error(request, "Failed to send password reset email. Please try again later.")
            
            return redirect('login')

        except User.DoesNotExist:
            messages.error(request, "No account found with that email address.")
            logger.warning(f"Password reset attempted for non-existent email: {email}")
            return render(request, 'public_panel/forgot_password.html')

    return render(request, 'public_panel/forgot_password.html')

def reset_password(request, uidb64, token):
    try:
        # Decode the user id
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
        
        # Verify the token
        if default_token_generator.check_token(user, token):
            if request.method == 'POST':
                password1 = request.POST.get('password1')
                password2 = request.POST.get('password2')
                
                if not password1 or not password2:
                    messages.error(request, "Please fill in both password fields.")
                    return render(request, 'public_panel/reset_password.html')
                
                if password1 != password2:
                    messages.error(request, "Passwords do not match.")
                    return render(request, 'public_panel/reset_password.html')
                
                # Validate password strength
                is_valid_password, password_error = validate_password(password1)
                if not is_valid_password:
                    messages.error(request, password_error)
                    return render(request, 'public_panel/reset_password.html')
                
                # Set new password
                user.set_password(password1)
                user.save()
                
                messages.success(request, "Your password has been reset successfully. You can now login with your new password.")
                return redirect('login')
            
            return render(request, 'public_panel/reset_password.html')
        else:
            messages.error(request, "The password reset link is invalid or has expired.")
            return redirect('forgetpassword')
            
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        messages.error(request, "The password reset link is invalid or has expired.")
        return redirect('forgetpassword')

# about 
def about_us(request):
    about_items = AboutUs.objects.filter(is_active=True).order_by('order', '-created_at')
    return render(request, 'public_panel/about_us.html', {
        'about_items': about_items
    })

from django.contrib import messages

# contact us form
def contact(request):
    if request.method == 'POST':
        try:
            data = request.POST
            name = data.get('name')
            email = data.get('email')
            subject = data.get('subject')
            message = data.get('message')

            if name and email and subject and message:
                contact_entry = ContactUs(
                    name=name,
                    email=email,
                    subject=subject,
                    message=message
                )
                contact_entry.save()
                messages.success(request, "Thank you for your message! We'll get back to you soon.")
                return redirect('contact')
            else:
                messages.error(request, "Please fill in all required fields.")
        except Exception as e:
            messages.error(request, "Something went wrong. Please try again.")
    
    return render(request, "public_panel/contact.html")



from django.utils.decorators import method_decorator

@method_decorator(login_required(login_url='customerregistration'), name='dispatch')
class ProfileView(View):
    def get(self, request):
        return render(request, 'public_panel/profile.html')


@method_decorator(login_required(login_url='/login/'), name='dispatch')
class UserBiddingDetailsView(View):
    def get(self, request):
        # All bids by the logged-in user
        user_all_bids = Bidnow.objects.filter(user=request.user).select_related('product').order_by('-created_at')

        # Find highest bids for each product
        highest_bids = {}
        for bid in user_all_bids:
            product_id = bid.product.id
            if product_id not in highest_bids:
                highest_bid = Bidnow.objects.filter(product_id=product_id).order_by('-bid_amount', 'created_at').first()
                highest_bids[product_id] = highest_bid

        # Only keep highest bids where user is the highest bidder
        user_highest_bids = [bid for bid in highest_bids.values() if bid.user == request.user]

        return render(request, 'public_panel/showbid.html', {
            'user_all_bids': user_all_bids,
            'user_highest_bids': user_highest_bids,
        })

@login_required(login_url='/login/')
def user_dashboard(request):
    """Comprehensive user dashboard"""
    try:
        from App.models import UserBehaviorProfile
        from django.db.models import Sum, Count
        from datetime import timedelta
        
        # Get user behavior profile
        user_profile, created = UserBehaviorProfile.objects.get_or_create(
            user=request.user,
            defaults={'risk_score': 0.0}
        )
        
        # User statistics
        user_bids = Bidnow.objects.filter(user=request.user)
        total_bids = user_bids.count()
        
        # Calculate winning bids
        winning_bids = 0
        for bid in user_bids:
            highest_bid = Bidnow.objects.filter(product=bid.product).order_by('-bid_amount').first()
            if highest_bid and highest_bid.user == request.user:
                winning_bids += 1
        
        # Total bid amount
        total_bid_amount = user_bids.aggregate(total=Sum('bid_amount'))['total'] or 0
        
        # Recent bids (last 5)
        recent_bids = user_bids.select_related('product').order_by('-created_at')[:5]
        
        # Add is_highest flag to recent bids
        for bid in recent_bids:
            highest_bid = Bidnow.objects.filter(product=bid.product).order_by('-bid_amount').first()
            bid.is_highest = highest_bid and highest_bid.user == request.user
        
        # Active auctions
        from django.utils import timezone
        now = timezone.now()
        active_auctions = Product.objects.filter(
            Auction=True, 
            event_ends__gt=now
        ).order_by('event_ends')[:5]
        
        # Add current bid and time left to active auctions
        for auction in active_auctions:
            highest_bid = Bidnow.objects.filter(product=auction).order_by('-bid_amount').first()
            auction.current_bid = highest_bid.bid_amount if highest_bid else auction.discounted_price
            
            time_left = auction.event_ends - now
            auction.time_left = int(time_left.total_seconds())
            
            if auction.time_left < 3600:  # Less than 1 hour
                auction.time_left_display = f"{auction.time_left // 60}m"
            elif auction.time_left < 86400:  # Less than 1 day
                auction.time_left_display = f"{auction.time_left // 3600}h"
            else:  # More than 1 day
                auction.time_left_display = f"{auction.time_left // 86400}d"
        
        # Bidding activity for chart (last 6 months)
        six_months_ago = now - timedelta(days=180)
        monthly_bids = user_bids.filter(created_at__gte=six_months_ago).extra(
            select={'month': "DATE_TRUNC('month', created_at)"}
        ).values('month').annotate(count=Count('id')).order_by('month')
        
        # Prepare chart data
        months = []
        counts = []
        for item in monthly_bids:
            months.append(item['month'].strftime('%b %Y'))
            counts.append(item['count'])
        
        user_stats = {
            'total_bids': total_bids,
            'winning_bids': winning_bids,
            'total_bid_amount': total_bid_amount,
            'risk_score': user_profile.risk_score,
        }
        
        bidding_activity = {
            'months': months,
            'counts': counts,
        }
        
        context = {
            'user_stats': user_stats,
            'user_profile': user_profile,
            'recent_bids': recent_bids,
            'active_auctions': active_auctions,
            'bidding_activity': bidding_activity,
        }
        
        return render(request, 'public_panel/user_dashboard.html', context)
        
    except Exception as e:
        messages.error(request, f"Error loading dashboard: {str(e)}")
        return render(request, 'public_panel/user_dashboard.html', {})
    
    #for search


def search(request):
    q = request.GET.get('q', '')

    results = AuctionItem.objects.filter(
        Q(title__icontains=q) | Q(description__icontains=q)
    )

    return render(request, 'public_panel/search.html', {'query': q, 'results': results})




# from django.utils import send_otp_via_email

# def custom_login_view(request):
#     if request.method == 'POST':
#         username_or_email = request.POST.get('username')
#         password = request.POST.get('password')

#         # Authenticate logic here...
#         user = authenticate(request, username=username_or_email, password=password)
#         if user is not None:
#             login(request, user)

#             # ✅ Send OTP after login
#             send_otp_via_email(user)

#             return redirect('home')  # or wherever you want
#         else:
#             messages.error(request, 'Invalid credentials')

#     return render(request, 'login.html')


# def register(request):
#     if request.method == 'POST':
#         username = request.POST.get('username')
#         email = request.POST.get('email')
#         password1 = request.POST.get('password1')
#         password2 = request.POST.get('password2')
#         user_type = request.POST.get('user_type')

#         if password1 != password2:
#             messages.error(request, "Passwords do not match.")
#             return redirect('register')

#         if User.objects.filter(username=username).exists():
#             messages.error(request, "Username already exists.")
#             return redirect('register')

#         if User.objects.filter(email=email).exists():
#             messages.error(request, "Email already exists.")
#             return redirect('register')

#         user = User.objects.create_user(username=username, email=email, password=password1 , user_type=user_type)
#         user.save()
#         messages.success(request, "Account created successfully!")
#         return redirect('login')
#     else:
#         return render(request, 'public_panel/register.html')


# ProductDetailView

        # else:
            #     temp= History.objects.filter(id=product.id)
            #     if temp.exists():
            #         product = Product.objects.get(pk=pk)
            #         temp= History.objects.get(id=product.id)
            #         highest = temp.history
            #         return render(request,'app/productdetail.html',{'product':product,'remaining_time':t3,'timeNow':t2,'fm':fm,'current_highest':highest})
            #     else:
            #         return render(request,'app/productdetail.html',{'product':product,'remaining_time':t3,'timeNow':t2,'fm':fm,'current_highest':'NO ONE HAS BIDDED THIS PRODUCT.. BE THE FIRST ONE'})


# from django.core.management.base import BaseCommand
# from django.utils.timezone import now

# class Command(BaseCommand):
#     help = 'Notify highest bidder when auction ends'

#     def handle(self, *args, **kwargs):
#         expired_products = Product.objects.filter(event_ends__lt=now(), Auction=True)

#         for product in expired_products:
#             # Get highest bid
#             highest_bid = Bidnow.objects.filter(product=product).order_by('-bid_amount').first()

#             if highest_bid:
#                 user = highest_bid.user
#                 subject = f"You've won the auction for {product.name}!"
#                 message = f"""
#                 Hi {user.username},

#                 Congratulations! 🎉

#                 You have won the auction for the product: {product.name}
#                 Your bid: Rs. {highest_bid.bid_amount}

#                 Please login to your account to proceed with payment or contact support if needed.

#                 Thanks,
#                 E-Auction Team
#                 """
#                 send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])

#                 self.stdout.write(self.style.SUCCESS(f"✅ Notified winner: {user.username} for product: {product.name}"))

#             # Mark auction as expired so we don't notify again
#             product.Auction = False
#             product.save()




# from django.utils import timezone

# def close_auction(product_id):
#     product = Product.objects.get(id=product_id)

#     # Ensure auction has ended
#     if product.event_ends and product.event_ends <= timezone.now() and not product.is_winner_notified:
#         # Get highest bid
#         highest_bid = Bidnow.objects.filter(product=product).order_by('-bid_amount').first()

#         if highest_bid:
#             # Save winner
#             winner_record, created = AuctionWinner.objects.get_or_create(
#                 product=product,
#                 defaults={
#                     'winner': highest_bid.user,
#                     'winning_bid': highest_bid.bid_amount
#                 }
#             )

#             if created:
#                 # Send email
#                 subject = '🎉 You Won the Auction!'
#                 message = f"""
# Hello {highest_bid.user.username},

# Congratulations! 🥳

# You won the auction for "{product.title}" with a bid of Rs. {highest_bid.bid_amount}.

# Please visit your account to proceed with the purchase.

# Regards,
# Auction Team
# """
#                 send_mail(subject, message, settings.EMAIL_HOST_USER, [highest_bid.user.email])

#                 # Mark product as notified
#                 product.is_winner_notified = True
#                 product.save()

# def notify_highest_bidder(product):
#     if not product.is_active or product.is_winner_notified:
#         return False  # Auction still active or already notified

#     highest_bid = Bidnow.objects.filter(product=product).order_by('-bid_amount').first()
#     if not highest_bid:
#         return False  # No bids

#     try:
#         subject = f"🎉 You Won the Auction for {product.product_name}!"
#         message = (
#             f"Hello {highest_bid.user.username},\n\n"
#             f"Congratulations! You won the auction for '{product.product_name}' "
#             f"with a bid of Rs. {highest_bid.bid_amount}.\n"
#             f"Please log in to your account to proceed with payment.\n\n"
#             f"Thank you,\nE-Auction Team"
#         )
#         send_mail(
#             subject,
#             message,
#             settings.DEFAULT_FROM_EMAIL,
#             [highest_bid.user.email],
#             fail_silently=False,
#         )

#         # Save winner record
#         AuctionWinner.objects.get_or_create(
#             product=product,
#             defaults={
#                 'winner': highest_bid.user,
#                 'winning_bid': highest_bid.bid_amount
#             }
#         )

#         # Mark product as notified
#         product.is_winner_notified = True
#         product.Auction = False
#         product.save()
#         return True
#     except Exception as e:
#         print(f"❌ Error sending email for product {product.product_name}: {e}")
#         return False
    

# for search options


# OTP email function removed - no longer needed for simple registration

    