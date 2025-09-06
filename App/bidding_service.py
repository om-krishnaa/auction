"""
Advanced Bidding Service with Real-time Validation and Auto-bidding
"""

import logging
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from django.utils import timezone
from django.db import transaction
from django.core.cache import cache
from django.contrib.auth import get_user_model

from .models import (
    Product, Bidnow, UserBehaviorProfile, BidValidation, 
    FraudAlert, BidIncrement, AutoBid, AuctionWinner
)
from .fraud_detection import fraud_detector, ml_detector
from .notifications import notification_service

User = get_user_model()
logger = logging.getLogger(__name__)

class AdvancedBiddingService:
    """
    Advanced bidding service with fraud detection, auto-bidding, and real-time validation
    """
    
    def __init__(self):
        self.min_bid_increment = Decimal('5.00')
        self.max_bid_increment = Decimal('1000.00')
    
    def place_bid(self, user: User, product: Product, bid_amount: Decimal, 
                  ip_address: str = None, user_agent: str = None) -> Dict:
        """
        Place a bid with comprehensive validation and fraud detection
        """
        try:
            # Check if auction is still active
            if not self._is_auction_active(product):
                return {
                    'success': False,
                    'message': 'Auction has ended',
                    'error_code': 'AUCTION_ENDED'
                }
            
            # Check if user has already bid on this product
            existing_bid = Bidnow.objects.filter(user=user, product=product).first()
            if existing_bid:
                return {
                    'success': False,
                    'message': 'You have already placed a bid on this product',
                    'error_code': 'ALREADY_BID'
                }
            
            # Run fraud detection
            fraud_result = fraud_detector.validate_bid(
                user, product, bid_amount, ip_address, user_agent
            )
            
            # Check if bid is valid
            if not fraud_result['is_valid']:
                return {
                    'success': False,
                    'message': 'Bid validation failed',
                    'error_code': 'VALIDATION_FAILED',
                    'details': fraud_result['errors']
                }
            
            # Check minimum bid requirements
            min_bid_result = self._validate_minimum_bid(product, bid_amount)
            if not min_bid_result['valid']:
                return {
                    'success': False,
                    'message': min_bid_result['message'],
                    'error_code': 'INSUFFICIENT_BID'
                }
            
            # Place the bid with transaction
            with transaction.atomic():
                bid = Bidnow.objects.create(
                    user=user,
                    product=product,
                    bid_amount=bid_amount
                )
                
                # Create bid validation records
                for validation in fraud_result['validations']:
                    BidValidation.objects.create(
                        bid=bid,
                        validation_type=validation['type'],
                        is_valid=validation['is_valid'],
                        risk_score=validation['risk_score'],
                        details=validation.get('details', {})
                    )
                
                # Update bid increments
                self._update_bid_increments(product, bid_amount)
                
                # Check for auto-bids and process them
                self._process_auto_bids(product, bid_amount)
                
                # Update user behavior profile
                self._update_user_profile(user, bid_amount, fraud_result)
                
                # Send notifications
                self._send_bid_notifications(product, bid, fraud_result)
                
                # Send real-time notification
                notification_service.send_bid_notification(bid, fraud_result['risk_score'])
            
            return {
                'success': True,
                'message': 'Bid placed successfully',
                'bid_id': bid.id,
                'risk_score': fraud_result['risk_score'],
                'warnings': fraud_result.get('warnings', [])
            }
            
        except Exception as e:
            logger.error(f"Error placing bid: {str(e)}")
            return {
                'success': False,
                'message': 'An error occurred while placing your bid',
                'error_code': 'SYSTEM_ERROR'
            }
    
    def place_auto_bid(self, user: User, product: Product, max_bid_amount: Decimal) -> Dict:
        """
        Set up auto-bidding for a user
        """
        try:
            if not self._is_auction_active(product):
                return {
                    'success': False,
                    'message': 'Auction has ended',
                    'error_code': 'AUCTION_ENDED'
                }
            
            # Check if user already has an auto-bid for this product
            existing_auto_bid = AutoBid.objects.filter(user=user, product=product).first()
            if existing_auto_bid:
                existing_auto_bid.max_bid_amount = max_bid_amount
                existing_auto_bid.save()
                return {
                    'success': True,
                    'message': 'Auto-bid updated successfully',
                    'auto_bid_id': existing_auto_bid.id
                }
            
            # Create new auto-bid
            auto_bid = AutoBid.objects.create(
                user=user,
                product=product,
                max_bid_amount=max_bid_amount
            )
            
            return {
                'success': True,
                'message': 'Auto-bid set up successfully',
                'auto_bid_id': auto_bid.id
            }
            
        except Exception as e:
            logger.error(f"Error setting up auto-bid: {str(e)}")
            return {
                'success': False,
                'message': 'An error occurred while setting up auto-bid',
                'error_code': 'SYSTEM_ERROR'
            }
    
    def get_current_bid_info(self, product: Product) -> Dict:
        """
        Get current bidding information for a product
        """
        try:
            # Get current highest bid
            highest_bid = Bidnow.objects.filter(product=product).order_by('-bid_amount').first()
            
            # Get bid increment info
            increment_info = BidIncrement.objects.filter(product=product).first()
            
            # Get total bid count
            total_bids = Bidnow.objects.filter(product=product).count()
            
            # Get unique bidders
            unique_bidders = Bidnow.objects.filter(product=product).values('user').distinct().count()
            
            # Calculate next minimum bid
            if highest_bid:
                current_highest = highest_bid.bid_amount
                min_increment = self._calculate_bid_increment(current_highest)
                next_minimum = current_highest + min_increment
            else:
                current_highest = product.discounted_price
                next_minimum = product.discounted_price + self.min_bid_increment
            
            return {
                'current_highest': float(current_highest),
                'next_minimum_bid': float(next_minimum),
                'total_bids': total_bids,
                'unique_bidders': unique_bidders,
                'highest_bidder': highest_bid.user.username if highest_bid else None,
                'time_left': self._get_time_left(product),
                'is_active': self._is_auction_active(product)
            }
            
        except Exception as e:
            logger.error(f"Error getting bid info: {str(e)}")
            return {}
    
    def get_user_bid_history(self, user: User, product: Product = None) -> List[Dict]:
        """
        Get user's bidding history
        """
        try:
            queryset = Bidnow.objects.filter(user=user)
            if product:
                queryset = queryset.filter(product=product)
            
            bids = queryset.select_related('product').order_by('-created_at')
            
            history = []
            for bid in bids:
                # Get validation results
                validations = BidValidation.objects.filter(bid=bid)
                risk_score = sum(v.risk_score for v in validations) / len(validations) if validations else 0
                
                history.append({
                    'id': bid.id,
                    'product_title': bid.product.title,
                    'bid_amount': float(bid.bid_amount),
                    'created_at': bid.created_at,
                    'risk_score': risk_score,
                    'is_highest': self._is_highest_bid(bid),
                    'product_id': bid.product.id
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting bid history: {str(e)}")
            return []
    
    def _is_auction_active(self, product: Product) -> bool:
        """Check if auction is still active"""
        if not product.event_ends:
            return True
        
        return timezone.now() < product.event_ends
    
    def _validate_minimum_bid(self, product: Product, bid_amount: Decimal) -> Dict:
        """Validate minimum bid requirements"""
        try:
            # Get current highest bid
            highest_bid = Bidnow.objects.filter(product=product).order_by('-bid_amount').first()
            
            if highest_bid:
                current_highest = highest_bid.bid_amount
                min_increment = self._calculate_bid_increment(current_highest)
                minimum_bid = current_highest + min_increment
            else:
                minimum_bid = product.discounted_price
            
            if bid_amount < minimum_bid:
                return {
                    'valid': False,
                    'message': f'Bid must be at least {minimum_bid}'
                }
            
            return {'valid': True}
            
        except Exception as e:
            logger.error(f"Error validating minimum bid: {str(e)}")
            return {'valid': False, 'message': 'Validation error'}
    
    def _calculate_bid_increment(self, current_bid: Decimal) -> Decimal:
        """Calculate appropriate bid increment"""
        if current_bid < 100:
            return Decimal('5.00')
        elif current_bid < 500:
            return Decimal('10.00')
        elif current_bid < 1000:
            return Decimal('25.00')
        elif current_bid < 5000:
            return Decimal('50.00')
        elif current_bid < 10000:
            return Decimal('100.00')
        else:
            return Decimal('250.00')
    
    def _update_bid_increments(self, product: Product, new_bid_amount: Decimal):
        """Update bid increment information"""
        try:
            increment_info, created = BidIncrement.objects.get_or_create(
                product=product,
                defaults={
                    'current_bid': new_bid_amount,
                    'next_minimum_bid': new_bid_amount + self._calculate_bid_increment(new_bid_amount),
                    'increment_amount': self._calculate_bid_increment(new_bid_amount)
                }
            )
            
            if not created:
                increment_info.current_bid = new_bid_amount
                increment_info.next_minimum_bid = new_bid_amount + self._calculate_bid_increment(new_bid_amount)
                increment_info.increment_amount = self._calculate_bid_increment(new_bid_amount)
                increment_info.save()
                
        except Exception as e:
            logger.error(f"Error updating bid increments: {str(e)}")
    
    def _process_auto_bids(self, product: Product, new_bid_amount: Decimal):
        """Process auto-bids when a new bid is placed"""
        try:
            # Get all active auto-bids for this product
            auto_bids = AutoBid.objects.filter(
                product=product,
                is_active=True,
                max_bid_amount__gt=new_bid_amount
            ).exclude(
                current_bid_amount__gte=new_bid_amount
            ).order_by('max_bid_amount')
            
            for auto_bid in auto_bids:
                # Calculate next bid amount
                next_bid = new_bid_amount + self._calculate_bid_increment(new_bid_amount)
                
                # Don't exceed max bid amount
                if next_bid > auto_bid.max_bid_amount:
                    next_bid = auto_bid.max_bid_amount
                
                # Place the auto-bid
                if next_bid > new_bid_amount:
                    self.place_bid(
                        auto_bid.user, 
                        product, 
                        next_bid,
                        ip_address="auto_bid",
                        user_agent="auto_bid_system"
                    )
                    
                    # Update auto-bid current amount
                    auto_bid.current_bid_amount = next_bid
                    auto_bid.save()
                    
                    # Break after first auto-bid to avoid infinite loops
                    break
                    
        except Exception as e:
            logger.error(f"Error processing auto-bids: {str(e)}")
    
    def _update_user_profile(self, user: User, bid_amount: Decimal, fraud_result: Dict):
        """Update user behavior profile"""
        try:
            profile, created = UserBehaviorProfile.objects.get_or_create(
                user=user,
                defaults={'risk_score': 0.0}
            )
            
            profile.total_bids += 1
            profile.last_bid_time = timezone.now()
            
            # Update average bid amount
            if profile.average_bid_amount == 0:
                profile.average_bid_amount = bid_amount
            else:
                profile.average_bid_amount = (
                    (profile.average_bid_amount * (profile.total_bids - 1) + bid_amount) 
                    / profile.total_bids
                )
            
            # Update risk score
            profile.risk_score = fraud_result['risk_score']
            
            # Flag user if risk is too high
            if fraud_result['risk_score'] >= 80:
                profile.is_flagged = True
                profile.suspicious_activity_count += 1
            
            profile.save()
            
        except Exception as e:
            logger.error(f"Error updating user profile: {str(e)}")
    
    def _is_highest_bid(self, bid: Bidnow) -> bool:
        """Check if a bid is the current highest bid for the product"""
        try:
            highest_bid = Bidnow.objects.filter(
                product=bid.product
            ).order_by('-bid_amount').first()
            
            return highest_bid and highest_bid.id == bid.id
            
        except Exception as e:
            logger.error(f"Error checking highest bid: {str(e)}")
            return False
    
    def _get_time_left(self, product: Product) -> Optional[int]:
        """Get time left in auction in seconds"""
        if not product.event_ends:
            return None
        
        time_left = product.event_ends - timezone.now()
        return max(0, int(time_left.total_seconds()))
    
    def _send_bid_notifications(self, product: Product, bid: Bidnow, fraud_result: Dict):
        """Send notifications for new bids"""
        try:
            # Cache recent bid for real-time updates
            cache_key = f"recent_bid_{product.id}"
            cache.set(cache_key, {
                'bidder': bid.user.username,
                'amount': float(bid.bid_amount),
                'timestamp': bid.created_at.isoformat(),
                'risk_score': fraud_result['risk_score']
            }, 300)  # 5 minutes
            
            # In a real implementation, you would send WebSocket notifications
            # or use Celery for async notifications
            
        except Exception as e:
            logger.error(f"Error sending notifications: {str(e)}")

class AuctionManager:
    """
    Manages auction lifecycle and winner determination
    """
    
    def __init__(self):
        self.bidding_service = AdvancedBiddingService()
    
    def end_auction(self, product: Product) -> Dict:
        """
        End an auction and determine the winner
        """
        try:
            with transaction.atomic():
                # Get highest bid
                highest_bid = Bidnow.objects.filter(
                    product=product
                ).order_by('-bid_amount').first()
                
                if not highest_bid:
                    return {
                        'success': False,
                        'message': 'No bids placed on this auction'
                    }
                
                # Create auction winner record
                winner, created = AuctionWinner.objects.get_or_create(
                    product=product,
                    defaults={
                        'winner': highest_bid.user,
                        'winning_bid': highest_bid.bid_amount
                    }
                )
                
                # Mark product as auction ended
                product.Auction = False
                product.is_winner_notified = True
                product.save()
                
                # Send winner notification
                self._notify_winner(highest_bid.user, product, highest_bid.bid_amount)
                
                # Send real-time winner notification
                notification_service.send_winner_notification(
                    product, highest_bid.user, float(highest_bid.bid_amount)
                )
                
                return {
                    'success': True,
                    'winner': highest_bid.user.username,
                    'winning_bid': float(highest_bid.bid_amount),
                    'winner_id': highest_bid.user.id
                }
                
        except Exception as e:
            logger.error(f"Error ending auction: {str(e)}")
            return {
                'success': False,
                'message': 'Error ending auction'
            }
    
    def _notify_winner(self, winner: User, product: Product, winning_bid: Decimal):
        """Send winner notification"""
        try:
            # In a real implementation, you would send email notifications
            logger.info(f"Winner notification: {winner.username} won {product.title} for {winning_bid}")
            
        except Exception as e:
            logger.error(f"Error notifying winner: {str(e)}")

# Global instances
bidding_service = AdvancedBiddingService()
auction_manager = AuctionManager()
