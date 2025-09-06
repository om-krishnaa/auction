"""
Auction Management System for eAuction Platform
Handles automatic auction closing, winner notifications, and status management
"""

import logging
from django.utils import timezone
from django.db.models import Max, Q
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import Product, Bidnow, AuctionWinner, User
from .notifications import notification_service

logger = logging.getLogger(__name__)

class AuctionManager:
    """Manages auction lifecycle including closing, winner selection, and notifications"""
    
    def __init__(self):
        self.notification_service = notification_service
    
    def close_expired_auctions(self):
        """Close all auctions that have passed their end time"""
        now = timezone.now()
        expired_auctions = Product.objects.filter(
            Auction=True,
            event_ends__lt=now,
            is_winner_notified=False
        )
        
        closed_count = 0
        for auction in expired_auctions:
            try:
                self._close_auction(auction)
                closed_count += 1
                logger.info(f"Closed auction: {auction.title}")
            except Exception as e:
                logger.error(f"Error closing auction {auction.id}: {str(e)}")
        
        return closed_count
    
    def _close_auction(self, auction):
        """Close a single auction and determine winner"""
        # Get the highest bid for this auction
        highest_bid = Bidnow.objects.filter(
            product=auction
        ).order_by('-bid_amount', 'created_at').first()
        
        if highest_bid:
            # Create auction winner record
            winner, created = AuctionWinner.objects.get_or_create(
                product=auction,
                defaults={
                    'winner': highest_bid.user,
                    'winning_bid': highest_bid.bid_amount,
                    'auction_ended_at': auction.event_ends,
                    'is_paid': False,
                    'is_delivered': False
                }
            )
            
            if created:
                # Mark auction as winner notified
                auction.is_winner_notified = True
                auction.Auction = False  # Close the auction
                auction.save()
                
                # Send winner notification
                self._send_winner_notification(winner)
                
                # Send notifications to other bidders
                self._notify_other_bidders(auction, highest_bid.user)
                
                logger.info(f"Auction {auction.title} closed. Winner: {highest_bid.user.username}")
            else:
                logger.warning(f"Auction {auction.title} already has a winner")
        else:
            # No bids on this auction
            auction.is_winner_notified = True
            auction.Auction = False
            auction.save()
            logger.info(f"Auction {auction.title} closed with no bids")
    
    def _send_winner_notification(self, auction_winner):
        """Send notification to auction winner"""
        try:
            # Send email notification
            self._send_winner_email(auction_winner)
            
            # Send in-app notification
            self.notification_service.send_winner_notification(
                auction_winner.product,
                auction_winner.winner,
                float(auction_winner.winning_bid)
            )
            
            logger.info(f"Winner notification sent to {auction_winner.winner.username}")
        except Exception as e:
            logger.error(f"Error sending winner notification: {str(e)}")
    
    def _send_winner_email(self, auction_winner):
        """Send email notification to winner"""
        try:
            subject = f"🎉 Congratulations! You won the auction for {auction_winner.product.title}"
            
            html_message = render_to_string('emails/auction_winner.html', {
                'winner': auction_winner.winner,
                'product': auction_winner.product,
                'winning_bid': auction_winner.winning_bid,
                'auction_winner': auction_winner
            })
            
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[auction_winner.winner.email],
                html_message=html_message,
                fail_silently=False
            )
        except Exception as e:
            logger.error(f"Error sending winner email: {str(e)}")
    
    def _notify_other_bidders(self, auction, winner):
        """Notify other bidders that they didn't win"""
        try:
            other_bidders = Bidnow.objects.filter(
                product=auction
            ).exclude(user=winner).values_list('user', flat=True).distinct()
            
            for user_id in other_bidders:
                user = User.objects.get(id=user_id)
                self.notification_service.send_auction_lost_notification(
                    auction, user, winner.username
                )
        except Exception as e:
            logger.error(f"Error notifying other bidders: {str(e)}")
    
    def get_auction_status(self, auction):
        """Get current status of an auction"""
        now = timezone.now()
        
        if not auction.Auction:
            return "closed"
        elif auction.event_ends and auction.event_ends < now:
            return "expired"
        elif auction.is_upcoming:
            return "upcoming"
        else:
            return "active"
    
    def get_auction_time_remaining(self, auction):
        """Get time remaining for an auction"""
        if not auction.event_ends:
            return None
        
        now = timezone.now()
        if auction.event_ends <= now:
            return None
        
        delta = auction.event_ends - now
        return {
            'total_seconds': int(delta.total_seconds()),
            'days': delta.days,
            'hours': delta.seconds // 3600,
            'minutes': (delta.seconds % 3600) // 60,
            'seconds': delta.seconds % 60
        }
    
    def start_auction(self, product):
        """Start an auction for a product"""
        if product.Auction:
            return False, "Auction already active"
        
        if not product.event_ends:
            return False, "Auction end time not set"
        
        product.Auction = True
        product.is_upcoming = False
        product.save()
        
        logger.info(f"Auction started for {product.title}")
        return True, "Auction started successfully"
    
    def pause_auction(self, product):
        """Pause an auction"""
        if not product.Auction:
            return False, "No active auction to pause"
        
        product.Auction = False
        product.save()
        
        logger.info(f"Auction paused for {product.title}")
        return True, "Auction paused successfully"
    
    def extend_auction(self, product, additional_minutes=30):
        """Extend auction end time"""
        if not product.Auction:
            return False, "No active auction to extend"
        
        if not product.event_ends:
            return False, "Auction end time not set"
        
        from datetime import timedelta
        product.event_ends += timedelta(minutes=additional_minutes)
        product.save()
        
        logger.info(f"Auction extended for {product.title} by {additional_minutes} minutes")
        return True, f"Auction extended by {additional_minutes} minutes"
    
    def get_auction_statistics(self):
        """Get overall auction statistics"""
        now = timezone.now()
        
        stats = {
            'total_auctions': Product.objects.filter(Auction=True).count(),
            'active_auctions': Product.objects.filter(
                Auction=True,
                event_ends__gt=now
            ).count(),
            'upcoming_auctions': Product.objects.filter(
                is_upcoming=True,
                Auction=False
            ).count(),
            'closed_auctions': Product.objects.filter(
                Auction=False,
                is_winner_notified=True
            ).count(),
            'expired_auctions': Product.objects.filter(
                Auction=True,
                event_ends__lt=now
            ).count(),
            'total_bids': Bidnow.objects.count(),
            'total_winners': AuctionWinner.objects.count(),
        }
        
        return stats

# Global auction manager instance
auction_manager = AuctionManager()
