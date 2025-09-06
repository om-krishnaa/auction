"""
Django management command to send auction notifications
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from App.models import Product
from App.notifications import notification_service
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Send auction ending notifications'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what notifications would be sent without actually sending them',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No notifications will be sent')
            )
        
        # Get active auctions
        now = timezone.now()
        active_auctions = Product.objects.filter(
            Auction=True,
            event_ends__gt=now
        )
        
        notifications_sent = 0
        
        for auction in active_auctions:
            if verbose:
                self.stdout.write(f"Processing: {auction.title}")
            
            if not dry_run:
                # Send auction ending notification
                if notification_service.send_auction_ending_notification(auction):
                    notifications_sent += 1
                    if verbose:
                        self.stdout.write(f"  Sent ending notification for: {auction.title}")
            else:
                # Check if notification would be sent
                time_left = auction.event_ends - now
                if time_left.total_seconds() <= 3600 and time_left.total_seconds() > 0:
                    notifications_sent += 1
                    if verbose:
                        self.stdout.write(f"  Would send ending notification for: {auction.title}")
        
        if notifications_sent > 0:
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(f'Would send {notifications_sent} notifications')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'Sent {notifications_sent} notifications')
                )
        else:
            self.stdout.write(
                self.style.SUCCESS('No notifications to send')
            )
