"""
Django management command to test the fraud detection system
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from decimal import Decimal
import random

from App.models import Product, Bidnow
from App.fraud_detection import fraud_detector
from App.bidding_service import bidding_service

User = get_user_model()

class Command(BaseCommand):
    help = 'Test the fraud detection system with various scenarios'

    def add_arguments(self, parser):
        parser.add_argument(
            '--scenarios',
            type=int,
            default=5,
            help='Number of test scenarios to run (default: 5)',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting fraud detection system test...')
        )
        
        try:
            # Get some test data
            users = list(User.objects.filter(user_type='user')[:10])
            products = list(Product.objects.filter(Auction=True)[:3])
            
            if not users or not products:
                self.stdout.write(
                    self.style.ERROR('Insufficient test data. Please run generate_sample_data first.')
                )
                return
            
            scenarios = options['scenarios']
            
            for i in range(scenarios):
                self.stdout.write(f"\n--- Test Scenario {i+1} ---")
                self._run_test_scenario(users, products, i+1)
            
            self.stdout.write(
                self.style.SUCCESS('\nFraud detection system test completed!')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during testing: {str(e)}')
            )

    def _run_test_scenario(self, users, products, scenario_num):
        """Run a specific test scenario"""
        user = random.choice(users)
        product = random.choice(products)
        
        # Different scenarios for testing
        if scenario_num == 1:
            # Normal bid
            bid_amount = product.discounted_price + Decimal('1000')
            self.stdout.write(f"Scenario: Normal bid by {user.username}")
            
        elif scenario_num == 2:
            # Suspiciously high bid
            bid_amount = product.discounted_price * Decimal('10')
            self.stdout.write(f"Scenario: Suspiciously high bid by {user.username}")
            
        elif scenario_num == 3:
            # Round number bid (suspicious)
            bid_amount = Decimal('50000')
            self.stdout.write(f"Scenario: Round number bid by {user.username}")
            
        elif scenario_num == 4:
            # Very new user
            new_user = random.choice(users)
            bid_amount = product.discounted_price + Decimal('500')
            self.stdout.write(f"Scenario: New user bid by {new_user.username}")
            user = new_user
            
        else:
            # Random bid
            bid_amount = product.discounted_price + Decimal(random.randint(100, 5000))
            self.stdout.write(f"Scenario: Random bid by {user.username}")
        
        # Test fraud detection
        result = fraud_detector.validate_bid(
            user=user,
            product=product,
            bid_amount=bid_amount,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        
        # Display results
        self.stdout.write(f"  Bid Amount: Rs. {bid_amount}")
        self.stdout.write(f"  Risk Score: {result['risk_score']:.1f}%")
        self.stdout.write(f"  Valid: {'Yes' if result['is_valid'] else 'No'}")
        
        if result['warnings']:
            self.stdout.write(f"  Warnings: {', '.join(result['warnings'])}")
        
        if result['errors']:
            self.stdout.write(f"  Errors: {', '.join(result['errors'])}")
        
        # Show validation details
        for validation in result['validations']:
            self.stdout.write(f"  {validation['type']}: {'✓' if validation['is_valid'] else '✗'} (Risk: {validation['risk_score']:.1f}%)")
