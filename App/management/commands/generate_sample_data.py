"""
Django management command to generate sample data for the auction platform
"""

from django.core.management.base import BaseCommand
from django.conf import settings
import logging

from App.sample_data_generator import sample_data_generator

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Generate sample data for the auction platform including users, products, and bidding history'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before generating new sample data',
        )
        parser.add_argument(
            '--users',
            type=int,
            default=50,
            help='Number of users to generate (default: 50)',
        )
        parser.add_argument(
            '--products',
            type=int,
            default=35,
            help='Number of products to generate (default: 35)',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting sample data generation...')
        )
        
        try:
            # Clear existing data if requested
            if options['clear']:
                self.stdout.write(
                    self.style.WARNING('Clearing existing data...')
                )
                self.clear_existing_data()
            
            # Generate sample data
            success = sample_data_generator.generate_all_sample_data()
            
            if success:
                self.stdout.write(
                    self.style.SUCCESS('Sample data generation completed successfully!')
                )
                self.stdout.write(
                    self.style.SUCCESS('You can now access the platform with:')
                )
                self.stdout.write(
                    self.style.SUCCESS('- Admin Panel: http://127.0.0.1:8000/arjun/')
                )
                self.stdout.write(
                    self.style.SUCCESS('- Public Panel: http://127.0.0.1:8000/')
                )
                self.stdout.write(
                    self.style.SUCCESS('- Admin Login: admin / admin123')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('Sample data generation failed!')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error generating sample data: {str(e)}')
            )
            logger.error(f"Error in generate_sample_data command: {str(e)}")

    def clear_existing_data(self):
        """Clear existing sample data"""
        from App.models import (
            User, Product, Brand, Bidnow, UserBehaviorProfile,
            Customer, AboutUs, ContactUs, SiteSetting, Feedback,
            FraudAlert, BidValidation, BidIncrement, AutoBid
        )
        
        # Clear in order to avoid foreign key constraints
        BidValidation.objects.all().delete()
        FraudAlert.objects.all().delete()
        BidIncrement.objects.all().delete()
        AutoBid.objects.all().delete()
        Bidnow.objects.all().delete()
        UserBehaviorProfile.objects.all().delete()
        Customer.objects.all().delete()
        Product.objects.all().delete()
        Brand.objects.all().delete()
        AboutUs.objects.all().delete()
        ContactUs.objects.all().delete()
        Feedback.objects.all().delete()
        SiteSetting.objects.all().delete()
        
        # Clear non-admin users
        User.objects.filter(user_type='user').delete()
        
        self.stdout.write(
            self.style.SUCCESS('Existing data cleared successfully!')
        )
