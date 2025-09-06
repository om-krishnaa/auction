from django.shortcuts import render, redirect,get_object_or_404
from admin_panel.form import ProductForm,AboutUsForm, SiteSettingForm, ContactUsForm
from App.models import Product,AboutUs, SiteSetting, ContactUs,Bidnow,UserProfile, UserBehaviorProfile, FraudAlert, BidValidation, AuctionWinner
from App.auction_manager import auction_manager
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth import authenticate, login as auth_login, get_user_model
from django.contrib.auth import get_user_model,logout
from django.contrib.auth.models import User
from django.db.models import Max, Count, Sum, Avg
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.db.models.functions import TruncMonth, TruncDate, ExtractMonth
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import json
from django.db.models import Q


User = get_user_model()

@login_required(login_url='/login/')
def index(request):
    # Get current date and date ranges
    today = timezone.now()
    thirty_days_ago = today - timedelta(days=30)
    seven_days_ago = today - timedelta(days=7)
    this_month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Base queryset excluding admins and superusers
    regular_users = User.objects.exclude(user_type='admin').exclude(is_superuser=True)
    
    # User Statistics - Only regular users
    total_users = regular_users.count()
    new_users_this_week = regular_users.filter(date_joined__gte=seven_days_ago).count()
    new_users_this_month = regular_users.filter(date_joined__gte=this_month_start).count()
    
    # Product Statistics
    total_products = Product.objects.count()
    active_auctions = Product.objects.filter(Auction=True, event_ends__gt=today).count()
    upcoming_auctions = Product.objects.filter(is_upcoming=True).count()
    
    # Bidding Statistics
    total_bids = Bidnow.objects.count()
    bids_this_week = Bidnow.objects.filter(created_at__gte=seven_days_ago).count()
    total_bid_value = Bidnow.objects.aggregate(total=Sum('bid_amount'))['total'] or 0
    
    # Fraud Detection Statistics
    total_fraud_alerts = FraudAlert.objects.count()
    unresolved_alerts = FraudAlert.objects.filter(is_resolved=False).count()
    high_risk_users = UserBehaviorProfile.objects.filter(risk_score__gte=70).count()
    
    # Get user types distribution - only for regular users
    user_types = regular_users.values('user_type').annotate(count=Count('id'))
    
    # Get recent users - only regular users
    recent_users = regular_users.order_by('-date_joined')[:5]
    
    # Get recent bids
    recent_bids = Bidnow.objects.select_related('user', 'product').order_by('-created_at')[:5]
    
    # Get recent fraud alerts
    recent_fraud_alerts = FraudAlert.objects.filter(is_resolved=False).order_by('-created_at')[:5]
    
    # Get monthly registration data for the charts
    monthly_data = (
        regular_users
        .annotate(month=TruncMonth('date_joined'))
        .values('month')
        .annotate(
            total_users=Count('id'),
            new_users=Count('id', filter=Q(date_joined__gte=thirty_days_ago))
        )
        .order_by('-month')[:6]
    )
    
    # Prepare data for the charts
    chart_labels = [data['month'].strftime('%B %Y') for data in monthly_data]
    total_users_data = [data['total_users'] for data in monthly_data]
    new_users_data = [data['new_users'] for data in monthly_data]
    
    # Convert to JSON for template
    chart_json = {
        'labels': json.dumps(chart_labels),
        'total_users': json.dumps(total_users_data),
        'new_users': json.dumps(new_users_data)
    }
    
    context = {
        'total_users': total_users,
        'new_users_this_week': new_users_this_week,
        'new_users_this_month': new_users_this_month,
        'total_products': total_products,
        'active_auctions': active_auctions,
        'upcoming_auctions': upcoming_auctions,
        'total_bids': total_bids,
        'bids_this_week': bids_this_week,
        'total_bid_value': total_bid_value,
        'total_fraud_alerts': total_fraud_alerts,
        'unresolved_alerts': unresolved_alerts,
        'high_risk_users': high_risk_users,
        'user_types': user_types,
        'recent_users': recent_users,
        'recent_bids': recent_bids,
        'recent_fraud_alerts': recent_fraud_alerts,
        'chart_json': chart_json,
    }
    
    return render(request, 'admin_panel/index.html', context)

def admin_login_view(request):
    # Redirect already logged-in admins or superusers
    if request.user.is_authenticated and (
        request.user.user_type == 'admin' or request.user.is_superuser
    ):
        return redirect('admin')

    if request.method == 'POST':
        username_or_email = request.POST.get('username')
        password = request.POST.get('password')

        if not username_or_email or not password:
            messages.error(request, "Please fill in both fields.")
            return redirect('admin_login')

        try:
            # Find user by email or username
            if '@' in username_or_email:
                user_obj = User.objects.get(email=username_or_email)
            else:
                user_obj = User.objects.get(username=username_or_email)

            # Authenticate using actual username
            user = authenticate(request, username=user_obj.username, password=password)

            if user:
                # Allow admin login only for superuser or user_type == 'admin'
                if user.is_superuser or user.user_type == 'admin':
                    auth_login(request, user)
                    messages.success(request, f"Welcome back, {user.username}!")
                    return redirect('admin')
                else:
                    messages.error(request, "Only admin or superuser accounts can log in here.")
            else:
                messages.error(request, "Invalid username/email or password.")
        except User.DoesNotExist:
            messages.error(request, "User not found.")

        return redirect('admin_login')

    return render(request, 'admin_panel/login.html')

def admin_register_view(request):
    """Simple admin registration without email verification"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        # Basic validation
        if not all([username, email, password, confirm_password]):
            messages.error(request, "All fields are required.")
            return render(request, 'admin_panel/register.html')

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'admin_panel/register.html')

        # Check if user already exists
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return render(request, 'admin_panel/register.html')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return render(request, 'admin_panel/register.html')

        # Create admin user
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                user_type='admin',
                is_staff=True
            )
            
            # Create user behavior profile
            from App.models import UserBehaviorProfile
            UserBehaviorProfile.objects.create(
                user=user,
                risk_score=0.0,
                account_age_days=0
            )
            
            messages.success(request, "Admin account created successfully! You can now login.")
            return redirect('admin_login')
            
        except Exception as e:
            messages.error(request, f"Error creating admin account: {str(e)}")
            return render(request, 'admin_panel/register.html')

    return render(request, 'admin_panel/register.html')


    
def logout_view(request):
    logout(request)
    return redirect('login')

def addproduct(request):
    return render(request,'admin_panel/addproduct.html')

def product_list(request):
    product = Product.objects.all()
    return render(request,'admin_panel/product.html',{
        'product':product
    })

def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('product-list')
    else:
        form = ProductForm()
    return render(request, 'admin_panel/form.html', {'form': form})

def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect('product-list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'admin_panel/form.html', {'form': form})

def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.delete()
    return redirect('product-list')

@login_required
def aboutus_list(request):
    aboutus = AboutUs.objects.all().order_by('order', '-created_at')
    return render(request, 'admin_panel/about.html', {
        'about_items': aboutus,
        'title': 'About Us Management'
    })

@login_required
def aboutus_create(request):
    if request.method == 'POST':
        form = AboutUsForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'About Us content created successfully!')
            return redirect('aboutus_list')
    else:
        form = AboutUsForm()
    
    return render(request, 'admin_panel/form.html', {
        'form': form, 
        'title': 'Create About Us',
        'submit_text': 'Create'
    })

@login_required
def aboutus_update(request, pk):
    aboutus = get_object_or_404(AboutUs, pk=pk)
    if request.method == 'POST':
        form = AboutUsForm(request.POST, request.FILES, instance=aboutus)
        if form.is_valid():
            form.save()
            messages.success(request, 'About Us content updated successfully!')
            return redirect('aboutus_list')
    else:
        form = AboutUsForm(instance=aboutus)
    
    return render(request, 'admin_panel/form.html', {
        'form': form, 
        'title': 'Update About Us',
        'submit_text': 'Update',
        'is_update': True
    })

@login_required
def aboutus_delete(request, pk):
    aboutus = get_object_or_404(AboutUs, pk=pk)
    if request.method == 'POST':
        aboutus.delete()
        messages.success(request, 'About Us content deleted successfully!')
        return redirect('aboutus_list')
    
    return render(request, 'admin_panel/confirm_delete.html', {
        'object': aboutus,
        'title': 'Delete About Us Content',
        'cancel_url': 'aboutus_list'
    })

@login_required
def aboutus_toggle_status(request, pk):
    aboutus = get_object_or_404(AboutUs, pk=pk)
    aboutus.is_active = not aboutus.is_active
    aboutus.save()
    status = 'activated' if aboutus.is_active else 'deactivated'
    messages.success(request, f'About Us content {status} successfully!')
    return redirect('aboutus_list')

@login_required
def aboutus_reorder(request):
    if request.method == 'POST':
        item_ids = request.POST.getlist('item_ids[]')
        for index, item_id in enumerate(item_ids):
            AboutUs.objects.filter(id=item_id).update(order=index)
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

# -------------------------
# ContactUs Views
# -------------------------

class ContactUsListView(ListView):
    model = ContactUs
    template_name = 'public_panel/contact_ushtml'
    context_object_name = 'contactus_list'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Contact Us List'
        return context

class ContactUsCreateView(CreateView):
    model = ContactUs
    form_class = ContactUsForm
    template_name = 'admin_panel/contactus_form.html'
    success_url = reverse_lazy('contactus_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add Contact Us'
        return context

class ContactUsUpdateView(UpdateView):
    model = ContactUs
    form_class = ContactUsForm
    template_name = 'public_panel/contactus_form.html'
    success_url = reverse_lazy('contactus_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Contact Us'
        return context

# class ContactUsDeleteView(DeleteView):
#     model = ContactUs
#     template_name = 'public_panel/confirm_delete.html'
#     success_url = reverse_lazy('contactus_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Delete Contact Us'
        return context

# -------------------------
# Product Views
# -------------------------

class ProductListView(ListView):
    model = Product
    template_name = 'public_panel/product_list.html'
    context_object_name = 'product_list'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Product List'
        return context

class ProductCreateView(CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'public_panel/product_form.html'
    success_url = reverse_lazy('product_list')



from django.shortcuts import render
from django.contrib.auth import get_user_model
from django.utils import timezone


User = get_user_model()

# View to count total users and render a simple template
def user_count_view(request):
    total_users = User.objects.count()
    return render(request, 'index.html', {'total_users': total_users})






# Admin dashboard view showing all key metrics
# from django.db.models import Max
# from django.utils import timezone

# def all_users_view(request):
#     now = timezone.now()

#     total_users = User.objects.count()
#     total_bids = Bidnow.objects.count()
#     total_auctions = Product.objects.count()
#     active_auctions = Product.objects.filter(event__lte=now, event_ends__gte=now).count()
    
#     recent_bids = Bidnow.objects.select_related('user', 'product').order_by('-created_at')[:3]
#     users = User.objects.all()
    
#     # Prepare highest bid mapping
#     highest_bids = Bidnow.objects.values('product_id').annotate(max_bid=Max('bid_amount'))
#     highest_bid_map = {item['product_id']: item['max_bid'] for item in highest_bids}

#     # Annotate bid status directly
#     user_bids = []
#     for bid in Bidnow.objects.select_related('user', 'product'):
#         status = "Highest" if bid.bid_amount == highest_bid_map.get(bid.product_id) else "Normal"
#         user_bids.append({
#             'user': bid.user,
#             'product': bid.product,
#             'bid_amount': bid.bid_amount,
#             'created_at': bid.created_at,
#             'status': status,
#         })
        

#     context = {
#         'total_users': total_users,
#         'total_bids': total_bids,
#         'total_auctions': total_auctions,
#         'active_auctions': active_auctions,
#         'recent_bids': recent_bids,
#         'users': users,
#         'user_bids': user_bids,
#     }

#     return render(request, 'admin_panel/user_dashboard.html', context)


def user_delete(request, pk):
    # Check if user is admin or has proper permissions
    if not request.user.is_authenticated or not (request.user.is_superuser or request.user.user_type == 'admin'):
        messages.error(request, "You don't have permission to delete users.")
        return redirect('admin')
    
    try:
        user = get_object_or_404(User, pk=pk)
        # Prevent self-deletion and superuser deletion
        if user == request.user:
            messages.error(request, "You cannot delete your own account.")
            return redirect('admin')
        if user.is_superuser:
            messages.error(request, "Superuser accounts cannot be deleted.")
            return redirect('admin')
            
        username = user.username
        user.delete()
        messages.success(request, f"User {username} has been deleted successfully.")
    except Exception as e:
        messages.error(request, f"Error deleting user: {str(e)}")
    
    return redirect('admin')




# admin_panel/views.py

def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    bids = Bidnow.objects.filter(product=product).order_by('-bid_amount')
    highest_bid = bids.first() if bids else None

    context = {
        'product': product,
        'bids': bids,
        'highest_bid': highest_bid,
    }
    return render(request, 'admin_panel/product_details.html', context)


from collections import defaultdict

def all_users_view(request):
    now = timezone.now()

    total_users = User.objects.count()
    total_bids = Bidnow.objects.count()
    total_auctions = Product.objects.count()
    active_auctions = Product.objects.filter(event__lte=now, event_ends__gte=now).count()

    recent_bids = Bidnow.objects.select_related('user', 'product').order_by('-created_at')[:3]
    users = User.objects.all()

    # Highest bid per product
    highest_bids = Bidnow.objects.values('product_id').annotate(max_bid=Max('bid_amount'))
    highest_bid_map = {item['product_id']: item['max_bid'] for item in highest_bids}

    # Group and sort bids by product
    bids_by_product = defaultdict(list)
    for bid in Bidnow.objects.select_related('user', 'product'):
        status = "Highest" if bid.bid_amount == highest_bid_map.get(bid.product_id) else " "
        bids_by_product[bid.product].append({
            'user': bid.user,
            'bid_amount': bid.bid_amount,
            'created_at': bid.created_at,
            'status': status,
        })

    # Sort each product's bid list by bid_amount descending
    for product in bids_by_product:
        bids_by_product[product].sort(key=lambda b: b['bid_amount'], reverse=True)

    context = {
        'total_users': total_users,
        'total_bids': total_bids,
        'total_auctions': total_auctions,
        'active_auctions': active_auctions,
        'recent_bids': recent_bids,
        'users': users,
        'bids_by_product': dict(bids_by_product),
    }

    return render(request, 'admin_panel/user_dashboard.html', context)

import csv
from django.http import HttpResponse
from django.db.models import Max
from App.models import Bidnow
from django.contrib.auth import get_user_model

User = get_user_model()

def export_bids_csv(request):
    bids = Bidnow.objects.select_related('user', 'product').order_by('-bid_amount')

    # Get the highest bid per product
    highest_bids = Bidnow.objects.values('product_id').annotate(max_bid=Max('bid_amount'))
    highest_bid_map = {item['product_id']: item['max_bid'] for item in highest_bids}

    # Set up CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="bidding_records.csv"'
    writer = csv.writer(response)

    # CSV header
    writer.writerow([
        'Username', 'Full Name', 'Email',
        'Product ID', 'Product Title',
        'Bid Amount (Rs.)', 'Bid Time', 'Status'
    ])

    # Write each bid row
    for bid in bids:
        user = bid.user
        full_name = f"{user.first_name} {user.last_name}".strip()
        is_winner = bid.bid_amount == highest_bid_map.get(bid.product.id)

        writer.writerow([
            user.username,
            full_name,
            user.email,
            bid.product.id,
            bid.product.title,
            bid.bid_amount,
            bid.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'Winner' if is_winner else ''
        ])

    return response

# coustomer feedback
def contact_us(request):
    data=ContactUs.objects.all()
    return render(request,'admin_panel/contact_us.html')


def feedback(request):
    # Get all feedback sorted by most recent first
    feedbacks = ContactUs.objects.all().order_by('-id')
    
    context = {
        'feedbacks': feedbacks,
        'title': 'Customer Feedback'
    }
    return render(request, 'admin_panel/feedback.html', context)

def sitesetting_list(request):
    settings = SiteSetting.objects.all()
    return render(request, 'admin_panel/sitesetting.html', {
        'settings': settings
    })

def sitesetting_create(request):
    if request.method == 'POST':
        form = SiteSettingForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('sitesetting_list')
    else:
        form = SiteSettingForm()
    return render(request, 'admin_panel/form.html', {'form': form})

def sitesetting_update(request, pk):
    setting = get_object_or_404(SiteSetting, pk=pk)
    if request.method == 'POST':
        form = SiteSettingForm(request.POST, instance=setting)
        if form.is_valid():
            form.save()
            return redirect('sitesetting_list')
    else:
        form = SiteSettingForm(instance=setting)
    return render(request, 'admin_panel/form.html', {'form': form})

# Fraud Detection Dashboard Views
@login_required
def fraud_dashboard(request):
    """Main fraud detection dashboard"""
    try:
        # Get fraud statistics
        total_alerts = FraudAlert.objects.count()
        unresolved_alerts = FraudAlert.objects.filter(is_resolved=False).count()
        high_risk_alerts = FraudAlert.objects.filter(
            is_resolved=False, 
            severity__in=['HIGH', 'CRITICAL']
        ).count()
        
        # Get recent fraud alerts
        recent_alerts = FraudAlert.objects.filter(
            is_resolved=False
        ).select_related('user', 'product').order_by('-created_at')[:10]
        
        # Get high-risk users
        high_risk_users = UserBehaviorProfile.objects.filter(
            risk_score__gte=70
        ).select_related('user').order_by('-risk_score')[:10]
        
        # Get suspicious bidding patterns
        suspicious_bids = BidValidation.objects.filter(
            is_valid=False
        ).select_related('bid__user', 'bid__product').order_by('-created_at')[:10]
        
        # Get fraud statistics by type
        alert_types = FraudAlert.objects.values('alert_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Get risk score distribution
        risk_distribution = {
            'low': UserBehaviorProfile.objects.filter(risk_score__lt=30).count(),
            'medium': UserBehaviorProfile.objects.filter(risk_score__gte=30, risk_score__lt=60).count(),
            'high': UserBehaviorProfile.objects.filter(risk_score__gte=60, risk_score__lt=80).count(),
            'critical': UserBehaviorProfile.objects.filter(risk_score__gte=80).count(),
        }
        
        context = {
            'total_alerts': total_alerts,
            'unresolved_alerts': unresolved_alerts,
            'high_risk_alerts': high_risk_alerts,
            'recent_alerts': recent_alerts,
            'high_risk_users': high_risk_users,
            'suspicious_bids': suspicious_bids,
            'alert_types': alert_types,
            'risk_distribution': risk_distribution,
        }
        
        return render(request, 'admin_panel/fraud_dashboard.html', context)
        
    except Exception as e:
        messages.error(request, f"Error loading fraud dashboard: {str(e)}")
        return render(request, 'admin_panel/fraud_dashboard.html', {})

# Auction Management Views
@login_required(login_url='/login/')
def auction_management(request):
    """Auction management dashboard"""
    try:
        # Get auction statistics
        stats = auction_manager.get_auction_statistics()
        
        # Get active auctions with time remaining
        now = timezone.now()
        active_auctions = Product.objects.filter(
            Auction=True,
            event_ends__gt=now
        ).order_by('event_ends')
        
        # Add time remaining to each auction
        for auction in active_auctions:
            auction.time_remaining = auction_manager.get_auction_time_remaining(auction)
        
        # Get upcoming auctions
        upcoming_auctions = Product.objects.filter(
            is_upcoming=True,
            Auction=False,
            event_ends__gt=now
        ).order_by('event_ends')
        
        # Get recent winners
        recent_winners = AuctionWinner.objects.select_related(
            'product', 'winner'
        ).order_by('-auction_ended_at')[:10]
        
        context = {
            'stats': stats,
            'active_auctions': active_auctions,
            'upcoming_auctions': upcoming_auctions,
            'recent_winners': recent_winners,
        }
        
        return render(request, 'admin_panel/auction_management.html', context)
        
    except Exception as e:
        messages.error(request, f"Error loading auction management: {str(e)}")
        return render(request, 'admin_panel/auction_management.html', {})

@login_required(login_url='/login/')
def close_auction_manual(request, product_id):
    """Manually close an auction"""
    try:
        product = get_object_or_404(Product, id=product_id)
        
        if not product.Auction:
            messages.warning(request, "This auction is not active")
            return redirect('auction_management')
        
        # Close the auction
        auction_manager._close_auction(product)
        messages.success(request, f"Auction '{product.title}' has been closed successfully")
        
    except Exception as e:
        messages.error(request, f"Error closing auction: {str(e)}")
    
    return redirect('auction_management')

@login_required(login_url='/login/')
def start_auction_manual(request, product_id):
    """Manually start an auction"""
    try:
        product = get_object_or_404(Product, id=product_id)
        
        success, message = auction_manager.start_auction(product)
        
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
        
    except Exception as e:
        messages.error(request, f"Error starting auction: {str(e)}")
    
    return redirect('auction_management')

@login_required(login_url='/login/')
def pause_auction_manual(request, product_id):
    """Manually pause an auction"""
    try:
        product = get_object_or_404(Product, id=product_id)
        
        success, message = auction_manager.pause_auction(product)
        
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
        
    except Exception as e:
        messages.error(request, f"Error pausing auction: {str(e)}")
    
    return redirect('auction_management')

@login_required(login_url='/login/')
def extend_auction(request, product_id):
    """Extend auction time"""
    if request.method == 'POST':
        try:
            product = get_object_or_404(Product, id=product_id)
            additional_minutes = int(request.POST.get('additional_minutes', 30))
            
            success, message = auction_manager.extend_auction(product, additional_minutes)
            
            if success:
                messages.success(request, message)
            else:
                messages.error(request, message)
            
        except Exception as e:
            messages.error(request, f"Error extending auction: {str(e)}")
    
    return redirect('auction_management')

@login_required(login_url='/login/')
def auction_winners(request):
    """View all auction winners"""
    try:
        winners = AuctionWinner.objects.select_related(
            'product', 'winner'
        ).order_by('-auction_ended_at')
        
        # Filter options
        status_filter = request.GET.get('status', 'all')
        if status_filter == 'unpaid':
            winners = winners.filter(is_paid=False)
        elif status_filter == 'paid':
            winners = winners.filter(is_paid=True, is_delivered=False)
        elif status_filter == 'delivered':
            winners = winners.filter(is_delivered=True)
        
        context = {
            'winners': winners,
            'status_filter': status_filter,
        }
        
        return render(request, 'admin_panel/auction_winners.html', context)
        
    except Exception as e:
        messages.error(request, f"Error loading auction winners: {str(e)}")
        return render(request, 'admin_panel/auction_winners.html', {})

@login_required(login_url='/login/')
def mark_winner_paid(request, winner_id):
    """Mark auction winner as paid"""
    try:
        winner = get_object_or_404(AuctionWinner, id=winner_id)
        winner.is_paid = True
        winner.save()
        
        messages.success(request, f"Marked {winner.winner.username} as paid for {winner.product.title}")
        
    except Exception as e:
        messages.error(request, f"Error marking winner as paid: {str(e)}")
    
    return redirect('auction_winners')

@login_required(login_url='/login/')
def mark_winner_delivered(request, winner_id):
    """Mark auction winner as delivered"""
    try:
        winner = get_object_or_404(AuctionWinner, id=winner_id)
        winner.is_delivered = True
        winner.save()
        
        messages.success(request, f"Marked {winner.winner.username} as delivered for {winner.product.title}")
        
    except Exception as e:
        messages.error(request, f"Error marking winner as delivered: {str(e)}")
    
    return redirect('auction_winners')

@login_required
def fraud_alerts_list(request):
    """List all fraud alerts with filtering options"""
    try:
        alerts = FraudAlert.objects.select_related('user', 'product', 'resolved_by').order_by('-created_at')
        
        # Apply filters
        severity_filter = request.GET.get('severity')
        status_filter = request.GET.get('status')
        alert_type_filter = request.GET.get('alert_type')
        
        if severity_filter:
            alerts = alerts.filter(severity=severity_filter)
        
        if status_filter == 'resolved':
            alerts = alerts.filter(is_resolved=True)
        elif status_filter == 'unresolved':
            alerts = alerts.filter(is_resolved=False)
        
        if alert_type_filter:
            alerts = alerts.filter(alert_type=alert_type_filter)
        
        context = {
            'alerts': alerts,
            'severity_choices': FraudAlert.SEVERITY_LEVELS,
            'alert_type_choices': FraudAlert.ALERT_TYPES,
        }
        
        return render(request, 'admin_panel/fraud_alerts.html', context)
        
    except Exception as e:
        messages.error(request, f"Error loading fraud alerts: {str(e)}")
        return render(request, 'admin_panel/fraud_alerts.html', {})

@login_required
def resolve_fraud_alert(request, alert_id):
    """Resolve a fraud alert"""
    try:
        alert = get_object_or_404(FraudAlert, id=alert_id)
        
        if request.method == 'POST':
            alert.is_resolved = True
            alert.resolved_by = request.user
            alert.resolved_at = timezone.now()
            alert.save()
            
            messages.success(request, f"Alert {alert_id} has been resolved.")
            return redirect('fraud_alerts_list')
        
        return render(request, 'admin_panel/resolve_alert.html', {'alert': alert})
        
    except Exception as e:
        messages.error(request, f"Error resolving alert: {str(e)}")
        return redirect('fraud_alerts_list')

@login_required
def user_risk_profiles(request):
    """View user risk profiles and behavior analysis"""
    try:
        profiles = UserBehaviorProfile.objects.select_related('user').order_by('-risk_score')
        
        # Apply filters
        risk_filter = request.GET.get('risk_level')
        flagged_filter = request.GET.get('flagged')
        
        if risk_filter:
            if risk_filter == 'low':
                profiles = profiles.filter(risk_score__lt=30)
            elif risk_filter == 'medium':
                profiles = profiles.filter(risk_score__gte=30, risk_score__lt=60)
            elif risk_filter == 'high':
                profiles = profiles.filter(risk_score__gte=60, risk_score__lt=80)
            elif risk_filter == 'critical':
                profiles = profiles.filter(risk_score__gte=80)
        
        if flagged_filter == 'true':
            profiles = profiles.filter(is_flagged=True)
        elif flagged_filter == 'false':
            profiles = profiles.filter(is_flagged=False)
        
        context = {
            'profiles': profiles,
        }
        
        return render(request, 'admin_panel/user_risk_profiles.html', context)
        
    except Exception as e:
        messages.error(request, f"Error loading user profiles: {str(e)}")
        return render(request, 'admin_panel/user_risk_profiles.html', {})

@login_required
def flag_user(request, user_id):
    """Flag or unflag a user"""
    try:
        user = get_object_or_404(User, id=user_id)
        profile, created = UserBehaviorProfile.objects.get_or_create(
            user=user,
            defaults={'risk_score': 0.0}
        )
        
        if request.method == 'POST':
            action = request.POST.get('action')
            
            if action == 'flag':
                profile.is_flagged = True
                profile.risk_score = max(profile.risk_score, 80)
                messages.success(request, f"User {user.username} has been flagged.")
            elif action == 'unflag':
                profile.is_flagged = False
                messages.success(request, f"User {user.username} has been unflagged.")
            
            profile.save()
            return redirect('user_risk_profiles')
        
        return render(request, 'admin_panel/flag_user.html', {
            'user': user,
            'profile': profile
        })
        
    except Exception as e:
        messages.error(request, f"Error flagging user: {str(e)}")
        return redirect('user_risk_profiles')

@login_required
def bid_validation_log(request):
    """View bid validation logs"""
    try:
        validations = BidValidation.objects.select_related(
            'bid__user', 'bid__product'
        ).order_by('-created_at')
        
        # Apply filters
        validation_type = request.GET.get('type')
        is_valid_filter = request.GET.get('is_valid')
        
        if validation_type:
            validations = validations.filter(validation_type=validation_type)
        
        if is_valid_filter == 'true':
            validations = validations.filter(is_valid=True)
        elif is_valid_filter == 'false':
            validations = validations.filter(is_valid=False)
        
        context = {
            'validations': validations,
            'validation_types': BidValidation.VALIDATION_TYPES,
        }
        
        return render(request, 'admin_panel/bid_validation_log.html', context)
        
    except Exception as e:
        messages.error(request, f"Error loading validation log: {str(e)}")
        return render(request, 'admin_panel/bid_validation_log.html', {})
