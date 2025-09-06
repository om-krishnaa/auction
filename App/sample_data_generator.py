"""
Sample Data Generator for Auction Platform
Creates realistic sample data including users, products, and bidding history
"""

import random
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from PIL import Image
import io

from .models import (
    User, Product, Brand, Bidnow, UserBehaviorProfile, 
    Customer, AboutUs, ContactUs, SiteSetting, Feedback
)

User = get_user_model()
logger = logging.getLogger(__name__)

class SampleDataGenerator:
    """
    Generate realistic sample data for the auction platform
    """
    
    def __init__(self):
        self.brands = [
            'Apple', 'Samsung', 'Dell', 'HP', 'Lenovo', 'Asus', 'Acer', 'MSI',
            'Sony', 'LG', 'OnePlus', 'Xiaomi', 'Huawei', 'Google', 'Microsoft'
        ]
        
        self.product_categories = {
            'M': 'Mobile',
            'L': 'Laptop', 
            'W': 'Watch'
        }
        
        self.mobile_models = [
            'iPhone 15 Pro', 'iPhone 14', 'Samsung Galaxy S24', 'Samsung Galaxy A54',
            'OnePlus 12', 'OnePlus 11', 'Xiaomi 14', 'Xiaomi 13T Pro',
            'Google Pixel 8', 'Google Pixel 7a', 'Huawei P60 Pro'
        ]
        
        self.laptop_models = [
            'MacBook Pro M3', 'MacBook Air M2', 'Dell XPS 13', 'Dell Inspiron 15',
            'HP Pavilion 15', 'HP EliteBook', 'Lenovo ThinkPad X1', 'Lenovo IdeaPad',
            'Asus ROG Strix', 'Asus ZenBook', 'MSI Gaming Laptop', 'Acer Aspire 5'
        ]
        
        self.watch_models = [
            'Apple Watch Series 9', 'Apple Watch SE', 'Samsung Galaxy Watch 6',
            'Samsung Galaxy Watch 5', 'Google Pixel Watch 2', 'OnePlus Watch 2'
        ]
        
        self.first_names = [
            'John', 'Jane', 'Michael', 'Sarah', 'David', 'Emily', 'Robert', 'Jessica',
            'William', 'Ashley', 'James', 'Amanda', 'Christopher', 'Jennifer', 'Daniel',
            'Lisa', 'Matthew', 'Nancy', 'Anthony', 'Karen', 'Mark', 'Betty', 'Donald',
            'Helen', 'Steven', 'Sandra', 'Paul', 'Donna', 'Andrew', 'Carol', 'Joshua',
            'Ruth', 'Kenneth', 'Sharon', 'Kevin', 'Michelle', 'Brian', 'Laura', 'George',
            'Sarah', 'Edward', 'Kimberly', 'Ronald', 'Deborah', 'Timothy', 'Dorothy'
        ]
        
        self.last_names = [
            'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller',
            'Davis', 'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez',
            'Wilson', 'Anderson', 'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin',
            'Lee', 'Perez', 'Thompson', 'White', 'Harris', 'Sanchez', 'Clark',
            'Ramirez', 'Lewis', 'Robinson', 'Walker', 'Young', 'Allen', 'King',
            'Wright', 'Scott', 'Torres', 'Nguyen', 'Hill', 'Flores', 'Green'
        ]
        
        self.cities = [
            'New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 'Philadelphia',
            'San Antonio', 'San Diego', 'Dallas', 'San Jose', 'Austin', 'Jacksonville',
            'Fort Worth', 'Columbus', 'Charlotte', 'San Francisco', 'Indianapolis',
            'Seattle', 'Denver', 'Washington', 'Boston', 'El Paso', 'Nashville',
            'Detroit', 'Oklahoma City', 'Portland', 'Las Vegas', 'Memphis', 'Louisville'
        ]
    
    def generate_all_sample_data(self):
        """Generate all sample data"""
        try:
            logger.info("Starting sample data generation...")
            
            # Generate brands first
            self.generate_brands()
            
            # Generate users and customers
            self.generate_users_and_customers()
            
            # Generate products
            self.generate_products()
            
            # Generate bidding history
            self.generate_bidding_history()
            
            # Generate user behavior profiles
            self.generate_user_behavior_profiles()
            
            # Generate site content
            self.generate_site_content()
            
            logger.info("Sample data generation completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Error generating sample data: {str(e)}")
            return False
    
    def generate_brands(self):
        """Generate brand data"""
        logger.info("Generating brands...")
        
        for brand_name in self.brands:
            brand, created = Brand.objects.get_or_create(name=brand_name)
            if created:
                logger.info(f"Created brand: {brand_name}")
    
    def generate_users_and_customers(self):
        """Generate users and customer profiles"""
        logger.info("Generating users and customers...")
        
        # Create admin user if not exists
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@eauction.com',
                'user_type': 'admin',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            logger.info("Created admin user")
        
        # Generate regular users
        for i in range(50):  # Generate 50 users
            first_name = random.choice(self.first_names)
            last_name = random.choice(self.last_names)
            username = f"{first_name.lower()}{last_name.lower()}{i}"
            email = f"{username}@example.com"
            
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                    'user_type': 'user',
                    'is_active': True
                }
            )
            
            if created:
                user.set_password('password123')
                user.save()
                
                # Create customer profile
                customer, created = Customer.objects.get_or_create(
                    user=user,
                    defaults={
                        'name': f"{first_name} {last_name}",
                        'locality': f"{random.randint(1, 100)} Main St",
                        'city': random.choice(self.cities)
                    }
                )
                
                logger.info(f"Created user: {username}")
    
    def generate_products(self):
        """Generate product data"""
        logger.info("Generating products...")
        
        # Get brands
        brands = list(Brand.objects.all())
        
        # Generate mobile products
        for i in range(15):
            model = random.choice(self.mobile_models)
            brand = random.choice(brands)
            
            # Generate realistic prices
            base_price = random.randint(20000, 120000)
            selling_price = base_price + random.randint(5000, 20000)
            
            # Set auction end time (1-30 days from now)
            event_ends = timezone.now() + timedelta(
                days=random.randint(1, 30),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )
            
            product, created = Product.objects.get_or_create(
                title=f"{brand.name} {model}",
                defaults={
                    'selling_price': selling_price,
                    'discounted_price': base_price,
                    'event': timezone.now(),
                    'event_ends': event_ends,
                    'description': self._generate_product_description('mobile', model),
                    'brand': brand.name,
                    'brands': brand,
                    'category': 'M',
                    'product_image': self._create_sample_image(),
                    'is_upcoming': random.choice([True, False]),
                    'Auction': random.choice([True, False])
                }
            )
            
            if created:
                logger.info(f"Created product: {product.title}")
        
        # Generate laptop products
        for i in range(12):
            model = random.choice(self.laptop_models)
            brand = random.choice(brands)
            
            base_price = random.randint(30000, 200000)
            selling_price = base_price + random.randint(10000, 50000)
            
            event_ends = timezone.now() + timedelta(
                days=random.randint(1, 30),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )
            
            product, created = Product.objects.get_or_create(
                title=f"{brand.name} {model}",
                defaults={
                    'selling_price': selling_price,
                    'discounted_price': base_price,
                    'event': timezone.now(),
                    'event_ends': event_ends,
                    'description': self._generate_product_description('laptop', model),
                    'brand': brand.name,
                    'brands': brand,
                    'category': 'L',
                    'product_image': self._create_sample_image(),
                    'is_upcoming': random.choice([True, False]),
                    'Auction': random.choice([True, False])
                }
            )
            
            if created:
                logger.info(f"Created product: {product.title}")
        
        # Generate watch products
        for i in range(8):
            model = random.choice(self.watch_models)
            brand = random.choice(brands)
            
            base_price = random.randint(10000, 80000)
            selling_price = base_price + random.randint(5000, 20000)
            
            event_ends = timezone.now() + timedelta(
                days=random.randint(1, 30),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )
            
            product, created = Product.objects.get_or_create(
                title=f"{brand.name} {model}",
                defaults={
                    'selling_price': selling_price,
                    'discounted_price': base_price,
                    'event': timezone.now(),
                    'event_ends': event_ends,
                    'description': self._generate_product_description('watch', model),
                    'brand': brand.name,
                    'brands': brand,
                    'category': 'W',
                    'product_image': self._create_sample_image(),
                    'is_upcoming': random.choice([True, False]),
                    'Auction': random.choice([True, False])
                }
            )
            
            if created:
                logger.info(f"Created product: {product.title}")
    
    def generate_bidding_history(self):
        """Generate realistic bidding history"""
        logger.info("Generating bidding history...")
        
        users = list(User.objects.filter(user_type='user'))
        products = list(Product.objects.filter(Auction=True))
        
        for product in products:
            # Random number of bidders (2-8)
            num_bidders = random.randint(2, 8)
            selected_users = random.sample(users, min(num_bidders, len(users)))
            
            current_bid = product.discounted_price
            bid_history = []
            
            for i, user in enumerate(selected_users):
                # Generate realistic bid increments
                if i == 0:
                    # First bid is close to starting price
                    bid_amount = current_bid + random.randint(100, 1000)
                else:
                    # Subsequent bids have realistic increments
                    increment = random.randint(500, 5000)
                    bid_amount = current_bid + increment
                
                # Add some randomness to bid timing
                bid_time = timezone.now() - timedelta(
                    days=random.randint(0, 10),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59)
                )
                
                bid, created = Bidnow.objects.get_or_create(
                    user=user,
                    product=product,
                    defaults={
                        'bid_amount': bid_amount,
                        'created_at': bid_time
                    }
                )
                
                if created:
                    current_bid = bid_amount
                    bid_history.append(bid)
                    logger.info(f"Created bid: {user.username} - {product.title} - Rs. {bid_amount}")
    
    def generate_user_behavior_profiles(self):
        """Generate user behavior profiles"""
        logger.info("Generating user behavior profiles...")
        
        users = User.objects.filter(user_type='user')
        
        for user in users:
            # Get user's bidding history
            user_bids = Bidnow.objects.filter(user=user)
            total_bids = user_bids.count()
            
            if total_bids > 0:
                # Calculate successful bids (highest bidder)
                successful_bids = 0
                total_bid_amount = 0
                last_bid_time = None
                
                for bid in user_bids:
                    total_bid_amount += bid.bid_amount
                    if last_bid_time is None or bid.created_at > last_bid_time:
                        last_bid_time = bid.created_at
                    
                    # Check if this is the highest bid for the product
                    highest_bid = Bidnow.objects.filter(
                        product=bid.product
                    ).order_by('-bid_amount').first()
                    
                    if highest_bid and highest_bid.user == user:
                        successful_bids += 1
                
                average_bid = total_bid_amount / total_bids if total_bids > 0 else 0
                
                # Calculate risk score based on behavior
                risk_score = self._calculate_risk_score(user, total_bids, successful_bids)
                
                profile, created = UserBehaviorProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'total_bids': total_bids,
                        'successful_bids': successful_bids,
                        'average_bid_amount': average_bid,
                        'last_bid_time': last_bid_time,
                        'risk_score': risk_score,
                        'account_age_days': (timezone.now() - user.date_joined).days,
                        'is_flagged': risk_score > 80
                    }
                )
                
                if created:
                    logger.info(f"Created behavior profile for {user.username} - Risk: {risk_score}")
    
    def generate_site_content(self):
        """Generate site content"""
        logger.info("Generating site content...")
        
        # Generate About Us content
        about_content = [
            {
                'title': 'About eAuction',
                'description': 'eAuction is a leading online auction platform that connects buyers and sellers in a secure, transparent, and efficient marketplace. We provide cutting-edge fraud detection and real-time bidding systems to ensure fair and safe transactions.',
                'order': 1
            },
            {
                'title': 'Our Mission',
                'description': 'To revolutionize the online auction industry by providing advanced fraud detection, real-time bidding, and exceptional user experience while maintaining the highest standards of security and transparency.',
                'order': 2
            },
            {
                'title': 'Advanced Security',
                'description': 'Our platform uses state-of-the-art machine learning algorithms and behavioral analysis to detect and prevent fraudulent activities, ensuring a safe environment for all users.',
                'order': 3
            }
        ]
        
        for content in about_content:
            about, created = AboutUs.objects.get_or_create(
                title=content['title'],
                defaults={
                    'description': content['description'],
                    'order': content['order'],
                    'is_active': True,
                    'image': self._create_sample_image()
                }
            )
            if created:
                logger.info(f"Created About Us: {content['title']}")
        
        # Generate Site Settings
        site_setting, created = SiteSetting.objects.get_or_create(
            id=1,
            defaults={
                'office_description': 'eAuction - Leading Online Auction Platform',
                'office_phone': 1234567890,
                'office_address': '123 Auction Street, New York, NY 10001',
                'office_email': 'info@eauction.com',
                'facebook': 'https://facebook.com/eauction',
                'x': 'https://twitter.com/eauction',
                'instagram': 'https://instagram.com/eauction',
                'linkedin': 'https://linkedin.com/company/eauction'
            }
        )
        if created:
            logger.info("Created site settings")
        
        # Generate sample feedback
        feedback_messages = [
            'Great platform! The fraud detection system gives me confidence in bidding.',
            'Excellent user experience. The real-time bidding is smooth and responsive.',
            'Love the advanced security features. Feel safe using this platform.',
            'Outstanding customer service and transparent auction process.',
            'The auto-bidding feature is fantastic. Highly recommended!'
        ]
        
        users = list(User.objects.filter(user_type='user')[:5])
        for i, message in enumerate(feedback_messages):
            if i < len(users):
                feedback, created = Feedback.objects.get_or_create(
                    name=users[i].get_full_name() or users[i].username,
                    email=users[i].email,
                    defaults={
                        'subject': 'Platform Feedback',
                        'message': message,
                        'is_read': random.choice([True, False])
                    }
                )
                if created:
                    logger.info(f"Created feedback from {users[i].username}")
    
    def _generate_product_description(self, category: str, model: str) -> str:
        """Generate realistic product descriptions"""
        descriptions = {
            'mobile': f"Latest {model} with advanced features, high-resolution display, powerful processor, and long-lasting battery. Perfect for both personal and professional use.",
            'laptop': f"High-performance {model} with cutting-edge technology, fast processing speed, excellent graphics, and premium build quality. Ideal for work and entertainment.",
            'watch': f"Smart {model} with health monitoring, fitness tracking, notifications, and stylish design. Water-resistant and durable for everyday wear."
        }
        return descriptions.get(category, f"Premium {model} with excellent features and quality.")
    
    def _create_sample_image(self):
        """Create a sample image for products"""
        try:
            # Create a simple colored image
            img = Image.new('RGB', (300, 300), color=(
                random.randint(100, 255),
                random.randint(100, 255),
                random.randint(100, 255)
            ))
            
            # Save to BytesIO
            img_io = io.BytesIO()
            img.save(img_io, format='JPEG')
            img_io.seek(0)
            
            # Create Django file
            return ContentFile(img_io.getvalue(), name='sample_product.jpg')
            
        except Exception as e:
            logger.error(f"Error creating sample image: {str(e)}")
            return None
    
    def _calculate_risk_score(self, user: User, total_bids: int, successful_bids: int) -> float:
        """Calculate risk score based on user behavior"""
        risk_score = 0.0
        
        # Account age factor
        account_age = (timezone.now() - user.date_joined).days
        if account_age < 1:
            risk_score += 30
        elif account_age < 7:
            risk_score += 15
        elif account_age < 30:
            risk_score += 5
        
        # Bidding pattern factor
        if total_bids > 0:
            success_rate = successful_bids / total_bids
            if success_rate > 0.8:  # Suspiciously high success rate
                risk_score += 25
            elif success_rate < 0.1:  # Very low success rate
                risk_score += 10
        
        # Add some randomness
        risk_score += random.uniform(-5, 15)
        
        return max(0, min(100, risk_score))

# Global instance
sample_data_generator = SampleDataGenerator()
