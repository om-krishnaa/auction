"""
Real-time Notification System for Fraud Detection and Bidding
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from django.utils import timezone
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model

from .models import FraudAlert, Bidnow, Product, UserBehaviorProfile

User = get_user_model()
logger = logging.getLogger(__name__)

class NotificationService:
    """
    Real-time notification service for fraud detection and bidding events
    """
    
    def __init__(self):
        self.cache_timeout = 300  # 5 minutes
    
    def send_fraud_alert_notification(self, alert: FraudAlert) -> bool:
        """
        Send real-time fraud alert notification to admins
        """
        try:
            # Cache the alert for real-time dashboard updates
            cache_key = f"fraud_alert_{alert.id}"
            cache.set(cache_key, {
                'id': alert.id,
                'user': alert.user.username,
                'type': alert.alert_type,
                'severity': alert.severity,
                'risk_score': alert.risk_score,
                'timestamp': alert.created_at.isoformat(),
                'description': alert.description
            }, self.cache_timeout)
            
            # Update fraud alert counter
            self._update_fraud_counter()
            
            # Send email notification for critical alerts
            if alert.severity in ['CRITICAL', 'HIGH']:
                self._send_email_notification(alert)
            
            # Log the notification
            logger.info(f"Fraud alert notification sent: {alert.alert_type} - {alert.user.username}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending fraud alert notification: {str(e)}")
            return False
    
    def send_bid_notification(self, bid: Bidnow, risk_score: float = 0.0) -> bool:
        """
        Send real-time bid notification
        """
        try:
            # Cache the bid for real-time updates
            cache_key = f"recent_bid_{bid.product.id}"
            cache.set(cache_key, {
                'bidder': bid.user.username,
                'amount': float(bid.bid_amount),
                'product': bid.product.title,
                'timestamp': bid.created_at.isoformat(),
                'risk_score': risk_score
            }, self.cache_timeout)
            
            # Update bid counter
            self._update_bid_counter()
            
            # Send high-risk bid alert
            if risk_score >= 70:
                self._create_high_risk_bid_alert(bid, risk_score)
            
            logger.info(f"Bid notification sent: {bid.user.username} - {bid.product.title}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending bid notification: {str(e)}")
            return False
    
    def send_auction_ending_notification(self, product: Product) -> bool:
        """
        Send notification when auction is ending soon
        """
        try:
            if not product.event_ends:
                return False
            
            time_left = product.event_ends - timezone.now()
            
            # Send notification if less than 1 hour remaining
            if time_left.total_seconds() <= 3600 and time_left.total_seconds() > 0:
                cache_key = f"auction_ending_{product.id}"
                cache.set(cache_key, {
                    'product': product.title,
                    'time_left': int(time_left.total_seconds()),
                    'current_bid': self._get_current_bid_amount(product),
                    'timestamp': timezone.now().isoformat()
                }, self.cache_timeout)
                
                logger.info(f"Auction ending notification: {product.title}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error sending auction ending notification: {str(e)}")
            return False
    
    def send_winner_notification(self, product: Product, winner: User, winning_bid: float) -> bool:
        """
        Send winner notification
        """
        try:
            cache_key = f"auction_winner_{product.id}"
            cache.set(cache_key, {
                'product': product.title,
                'winner': winner.username,
                'winning_bid': winning_bid,
                'timestamp': timezone.now().isoformat()
            }, self.cache_timeout * 2)  # Keep winner notification longer
            
            # Send email to winner
            self._send_winner_email(winner, product, winning_bid)
            
            logger.info(f"Winner notification sent: {winner.username} - {product.title}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending winner notification: {str(e)}")
            return False
    
    def get_recent_notifications(self, limit: int = 10) -> List[Dict]:
        """
        Get recent notifications for dashboard
        """
        try:
            notifications = []
            
            # Get recent fraud alerts
            recent_alerts = FraudAlert.objects.filter(
                is_resolved=False
            ).order_by('-created_at')[:limit//2]
            
            for alert in recent_alerts:
                notifications.append({
                    'type': 'fraud_alert',
                    'severity': alert.severity,
                    'message': f"Fraud alert: {alert.get_alert_type_display()} for {alert.user.username}",
                    'timestamp': alert.created_at,
                    'risk_score': alert.risk_score
                })
            
            # Get recent high-value bids
            recent_bids = Bidnow.objects.select_related('user', 'product').order_by('-created_at')[:limit//2]
            
            for bid in recent_bids:
                # Get risk score from user profile
                try:
                    profile = UserBehaviorProfile.objects.get(user=bid.user)
                    risk_score = profile.risk_score
                except UserBehaviorProfile.DoesNotExist:
                    risk_score = 0
                
                if risk_score >= 50:  # Only show high-risk bids
                    notifications.append({
                        'type': 'high_risk_bid',
                        'severity': 'medium' if risk_score < 70 else 'high',
                        'message': f"High-risk bid: {bid.user.username} bid Rs. {bid.bid_amount} on {bid.product.title}",
                        'timestamp': bid.created_at,
                        'risk_score': risk_score
                    })
            
            # Sort by timestamp and return limited results
            notifications.sort(key=lambda x: x['timestamp'], reverse=True)
            return notifications[:limit]
            
        except Exception as e:
            logger.error(f"Error getting recent notifications: {str(e)}")
            return []
    
    def get_dashboard_stats(self) -> Dict:
        """
        Get real-time dashboard statistics
        """
        try:
            now = timezone.now()
            last_hour = now - timedelta(hours=1)
            last_24_hours = now - timedelta(hours=24)
            
            stats = {
                'total_alerts': FraudAlert.objects.count(),
                'unresolved_alerts': FraudAlert.objects.filter(is_resolved=False).count(),
                'high_risk_alerts': FraudAlert.objects.filter(
                    is_resolved=False, 
                    severity__in=['HIGH', 'CRITICAL']
                ).count(),
                'alerts_last_hour': FraudAlert.objects.filter(created_at__gte=last_hour).count(),
                'alerts_last_24h': FraudAlert.objects.filter(created_at__gte=last_24_hours).count(),
                'total_bids': Bidnow.objects.count(),
                'bids_last_hour': Bidnow.objects.filter(created_at__gte=last_hour).count(),
                'bids_last_24h': Bidnow.objects.filter(created_at__gte=last_24_hours).count(),
                'high_risk_users': UserBehaviorProfile.objects.filter(risk_score__gte=70).count(),
                'flagged_users': UserBehaviorProfile.objects.filter(is_flagged=True).count(),
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting dashboard stats: {str(e)}")
            return {}
    
    def _update_fraud_counter(self):
        """Update fraud alert counter in cache"""
        try:
            cache_key = 'fraud_alert_counter'
            current_count = cache.get(cache_key, 0)
            cache.set(cache_key, current_count + 1, self.cache_timeout)
        except Exception as e:
            logger.error(f"Error updating fraud counter: {str(e)}")
    
    def _update_bid_counter(self):
        """Update bid counter in cache"""
        try:
            cache_key = 'bid_counter'
            current_count = cache.get(cache_key, 0)
            cache.set(cache_key, current_count + 1, self.cache_timeout)
        except Exception as e:
            logger.error(f"Error updating bid counter: {str(e)}")
    
    def _get_current_bid_amount(self, product: Product) -> float:
        """Get current highest bid amount for a product"""
        try:
            highest_bid = Bidnow.objects.filter(product=product).order_by('-bid_amount').first()
            return float(highest_bid.bid_amount) if highest_bid else float(product.discounted_price)
        except Exception:
            return float(product.discounted_price)
    
    def _create_high_risk_bid_alert(self, bid: Bidnow, risk_score: float):
        """Create high-risk bid alert"""
        try:
            severity = 'CRITICAL' if risk_score >= 90 else 'HIGH'
            
            FraudAlert.objects.create(
                user=bid.user,
                product=bid.product,
                bid=bid,
                alert_type='HIGH_RISK_BID',
                severity=severity,
                description=f"High-risk bid detected: Rs. {bid.bid_amount} (Risk Score: {risk_score:.1f}%)",
                risk_score=risk_score
            )
        except Exception as e:
            logger.error(f"Error creating high-risk bid alert: {str(e)}")
    
    def _send_email_notification(self, alert: FraudAlert):
        """Send email notification for critical alerts"""
        try:
            if not hasattr(settings, 'EMAIL_HOST_USER') or not settings.EMAIL_HOST_USER:
                return
            
            # Get admin users
            admin_users = User.objects.filter(
                user_type='admin'
            ).values_list('email', flat=True)
            
            if not admin_users:
                return
            
            subject = f"🚨 Fraud Alert: {alert.get_alert_type_display()}"
            message = f"""
            A {alert.severity.lower()} risk fraud alert has been triggered:
            
            User: {alert.user.username}
            Alert Type: {alert.get_alert_type_display()}
            Risk Score: {alert.risk_score:.1f}%
            Description: {alert.description}
            Time: {alert.created_at}
            
            Please review this alert in the admin dashboard.
            """
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=list(admin_users),
                fail_silently=True
            )
            
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")
    
    def _send_winner_email(self, winner: User, product: Product, winning_bid: float):
        """Send winner notification email"""
        try:
            if not hasattr(settings, 'EMAIL_HOST_USER') or not settings.EMAIL_HOST_USER:
                return
            
            subject = "🎉 Congratulations! You Won the Auction"
            message = f"""
            Dear {winner.username},
            
            Congratulations! You have won the auction for "{product.title}" with a bid of Rs. {winning_bid:,.2f}.
            
            Please log in to your account to proceed with the purchase and payment.
            
            Thank you for using eAuction!
            
            Best regards,
            The eAuction Team
            """
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[winner.email],
                fail_silently=True
            )
            
        except Exception as e:
            logger.error(f"Error sending winner email: {str(e)}")

# Global instance
notification_service = NotificationService()
