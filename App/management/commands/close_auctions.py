"""
Django management command to close expired auctions
Run this command periodically (e.g., via cron job) to automatically close expired auctions
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from App.auction_manager import auction_manager
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Close expired auctions and notify winners'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be closed without actually closing auctions',
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
                self.style.WARNING('DRY RUN MODE - No auctions will be closed')
            )
        
        # Get expired auctions
        now = timezone.now()
        expired_auctions = auction_manager.get_auction_statistics()['expired_auctions']
        
        if verbose:
            self.stdout.write(f"Found {expired_auctions} expired auctions")
        
        if expired_auctions == 0:
            self.stdout.write(
                self.style.SUCCESS('No expired auctions found')
            )
            return
        
        if not dry_run:
            # Close expired auctions
            closed_count = auction_manager.close_expired_auctions()
            
            if closed_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully closed {closed_count} expired auctions'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING('No auctions were closed')
                )
        else:
            self.stdout.write(
                self.style.WARNING(f'Would close {expired_auctions} expired auctions')
            )
        
        # Show statistics
        if verbose:
            stats = auction_manager.get_auction_statistics()
            self.stdout.write('\nAuction Statistics:')
            self.stdout.write(f"  Total Auctions: {stats['total_auctions']}")
            self.stdout.write(f"  Active Auctions: {stats['active_auctions']}")
            self.stdout.write(f"  Upcoming Auctions: {stats['upcoming_auctions']}")
            self.stdout.write(f"  Closed Auctions: {stats['closed_auctions']}")
            self.stdout.write(f"  Expired Auctions: {stats['expired_auctions']}")
            self.stdout.write(f"  Total Bids: {stats['total_bids']}")
            self.stdout.write(f"  Total Winners: {stats['total_winners']}")
