"""
Django management command to start upcoming auctions
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from App.models import Product
from App.auction_manager import auction_manager
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Start upcoming auctions that are ready to begin'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be started without actually starting auctions',
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
                self.style.WARNING('DRY RUN MODE - No auctions will be started')
            )
        
        # Get upcoming auctions that are ready to start
        now = timezone.now()
        upcoming_auctions = Product.objects.filter(
            is_upcoming=True,
            Auction=False,
            event_ends__gt=now
        )
        
        if verbose:
            self.stdout.write(f"Found {upcoming_auctions.count()} upcoming auctions")
        
        started_count = 0
        for auction in upcoming_auctions:
            if verbose:
                self.stdout.write(f"Processing: {auction.title}")
            
            if not dry_run:
                success, message = auction_manager.start_auction(auction)
                if success:
                    started_count += 1
                    if verbose:
                        self.stdout.write(f"  Started: {auction.title}")
                else:
                    self.stdout.write(
                        self.style.WARNING(f"  Failed to start {auction.title}: {message}")
                    )
            else:
                started_count += 1
                if verbose:
                    self.stdout.write(f"  Would start: {auction.title}")
        
        if started_count > 0:
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(f'Would start {started_count} auctions')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully started {started_count} auctions')
                )
        else:
            self.stdout.write(
                self.style.SUCCESS('No auctions ready to start')
            )
