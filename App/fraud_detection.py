"""
Advanced Fraud Detection System for Auction Platform
Implements multiple fraud detection algorithms and ML-based risk assessment
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Tuple, Optional
from django.utils import timezone
from django.db.models import Q, Count, Avg, Max, Min
from django.core.cache import cache
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import numpy as np
import pandas as pd

from .models import (
    User, Bidnow, Product, UserBehaviorProfile, 
    BidValidation, FraudAlert, BidIncrement, AutoBid
)

logger = logging.getLogger(__name__)

class FraudDetectionEngine:
    """
    Comprehensive fraud detection engine with multiple algorithms
    """
    
    def __init__(self):
        self.risk_thresholds = {
            'low': 30,
            'medium': 60,
            'high': 80,
            'critical': 90
        }
        
    def validate_bid(self, user: User, product: Product, bid_amount: Decimal, 
                    ip_address: str = None, user_agent: str = None) -> Dict:
        """
        Main bid validation function that runs all fraud checks
        """
        validation_result = {
            'is_valid': True,
            'risk_score': 0.0,
            'warnings': [],
            'errors': [],
            'validations': []
        }
        
        try:
            # Get or create user behavior profile
            profile, created = UserBehaviorProfile.objects.get_or_create(
                user=user,
                defaults={'risk_score': 0.0}
            )
            
            # Run all validation checks
            validations = [
                self._validate_bid_amount(user, product, bid_amount),
                self._validate_bid_velocity(user, product),
                self._validate_user_behavior(user, profile),
                self._validate_bid_patterns(user, product, bid_amount),
                self._validate_account_age(user, profile),
                self._validate_concurrent_bids(user, product),
                self._validate_ip_consistency(user, ip_address),
                self._validate_device_fingerprint(user, user_agent),
            ]
            
            # Process validation results
            total_risk = 0
            for validation in validations:
                if validation:
                    validation_result['validations'].append(validation)
                    total_risk += validation.get('risk_score', 0)
                    
                    if not validation.get('is_valid', True):
                        validation_result['is_valid'] = False
                        validation_result['errors'].append(validation.get('message', 'Validation failed'))
                    elif validation.get('warning'):
                        validation_result['warnings'].append(validation.get('warning'))
            
            # Calculate final risk score
            validation_result['risk_score'] = min(total_risk, 100.0)
            
            # Update user behavior profile
            self._update_user_profile(user, profile, bid_amount, validation_result)
            
            # Create fraud alert if risk is high
            if validation_result['risk_score'] >= self.risk_thresholds['high']:
                alert = self._create_fraud_alert(user, product, bid_amount, validation_result)
                if alert:
                    # Send real-time notification
                    from .notifications import notification_service
                    notification_service.send_fraud_alert_notification(alert)
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error in bid validation: {str(e)}")
            return {
                'is_valid': False,
                'risk_score': 100.0,
                'errors': ['System error during validation'],
                'warnings': [],
                'validations': []
            }
    
    def _validate_bid_amount(self, user: User, product: Product, bid_amount: Decimal) -> Dict:
        """Validate bid amount against product and user history"""
        try:
            # Get current highest bid
            highest_bid = Bidnow.objects.filter(product=product).order_by('-bid_amount').first()
            current_highest = highest_bid.bid_amount if highest_bid else product.discounted_price
            
            # Calculate minimum bid increment
            min_increment = self._calculate_bid_increment(current_highest)
            minimum_bid = current_highest + min_increment
            
            risk_score = 0
            is_valid = True
            message = ""
            
            # Check if bid meets minimum requirement
            if bid_amount < minimum_bid:
                is_valid = False
                message = f"Bid must be at least {minimum_bid}"
                risk_score = 50
            
            # Check for suspiciously high bids
            elif bid_amount > current_highest * 5:  # More than 5x current bid
                risk_score = 40
                message = "Bid amount is unusually high"
            
            # Check against user's average bid
            user_avg = UserBehaviorProfile.objects.filter(user=user).first()
            if user_avg and user_avg.average_bid_amount > 0:
                if bid_amount > user_avg.average_bid_amount * 3:
                    risk_score += 20
                    message = "Bid significantly higher than user's average"
            
            return {
                'type': 'AMOUNT',
                'is_valid': is_valid,
                'risk_score': risk_score,
                'message': message,
                'details': {
                    'bid_amount': float(bid_amount),
                    'minimum_required': float(minimum_bid),
                    'current_highest': float(current_highest)
                }
            }
            
        except Exception as e:
            logger.error(f"Error in amount validation: {str(e)}")
            return None
    
    def _validate_bid_velocity(self, user: User, product: Product) -> Dict:
        """Check for rapid bidding patterns (bid sniping)"""
        try:
            now = timezone.now()
            time_windows = [
                (1, 60),    # 1 minute
                (5, 300),   # 5 minutes
                (15, 900),  # 15 minutes
                (60, 3600), # 1 hour
            ]
            
            max_risk = 0
            velocity_warnings = []
            
            for window_name, seconds in time_windows:
                start_time = now - timedelta(seconds=seconds)
                recent_bids = Bidnow.objects.filter(
                    user=user,
                    created_at__gte=start_time
                ).count()
                
                # Define thresholds for each time window
                thresholds = {1: 3, 5: 8, 15: 15, 60: 25}
                threshold = thresholds.get(window_name, 10)
                
                if recent_bids > threshold:
                    risk = min((recent_bids - threshold) * 10, 50)
                    max_risk = max(max_risk, risk)
                    velocity_warnings.append(
                        f"{recent_bids} bids in {window_name} minute(s)"
                    )
            
            return {
                'type': 'VELOCITY',
                'is_valid': max_risk < 40,
                'risk_score': max_risk,
                'warning': f"High bidding velocity: {', '.join(velocity_warnings)}" if velocity_warnings else None,
                'details': {
                    'recent_bids': recent_bids,
                    'warnings': velocity_warnings
                }
            }
            
        except Exception as e:
            logger.error(f"Error in velocity validation: {str(e)}")
            return None
    
    def _validate_user_behavior(self, user: User, profile: UserBehaviorProfile) -> Dict:
        """Analyze user behavior patterns"""
        try:
            risk_score = 0
            warnings = []
            
            # Check account age
            account_age = (timezone.now() - user.date_joined).days
            if account_age < 1:
                risk_score += 30
                warnings.append("Very new account")
            elif account_age < 7:
                risk_score += 15
                warnings.append("New account")
            
            # Check bid success rate
            if profile.total_bids > 0:
                success_rate = profile.successful_bids / profile.total_bids
                if success_rate > 0.8:  # Suspiciously high success rate
                    risk_score += 25
                    warnings.append("Unusually high bid success rate")
                elif success_rate < 0.1:  # Very low success rate
                    risk_score += 10
                    warnings.append("Very low bid success rate")
            
            # Check for suspicious activity history
            if profile.suspicious_activity_count > 0:
                risk_score += profile.suspicious_activity_count * 5
                warnings.append(f"{profile.suspicious_activity_count} previous suspicious activities")
            
            # Check if user is already flagged
            if profile.is_flagged:
                risk_score += 40
                warnings.append("User account is flagged")
            
            return {
                'type': 'BEHAVIOR',
                'is_valid': risk_score < 50,
                'risk_score': risk_score,
                'warning': '; '.join(warnings) if warnings else None,
                'details': {
                    'account_age_days': account_age,
                    'total_bids': profile.total_bids,
                    'success_rate': profile.successful_bids / profile.total_bids if profile.total_bids > 0 else 0,
                    'suspicious_activities': profile.suspicious_activity_count,
                    'is_flagged': profile.is_flagged
                }
            }
            
        except Exception as e:
            logger.error(f"Error in behavior validation: {str(e)}")
            return None
    
    def _validate_bid_patterns(self, user: User, product: Product, bid_amount: Decimal) -> Dict:
        """Detect suspicious bidding patterns"""
        try:
            risk_score = 0
            patterns = []
            
            # Check for round number bids (suspicious)
            if bid_amount % 100 == 0 and bid_amount > 1000:
                risk_score += 10
                patterns.append("Round number bid")
            
            # Check for sequential bidding patterns
            user_bids = Bidnow.objects.filter(user=user, product=product).order_by('-created_at')[:5]
            if len(user_bids) >= 3:
                amounts = [float(bid.bid_amount) for bid in user_bids]
                if self._is_sequential_pattern(amounts):
                    risk_score += 20
                    patterns.append("Sequential bidding pattern")
            
            # Check for bid timing patterns (last minute bidding)
            if product.event_ends:
                time_left = product.event_ends - timezone.now()
                if time_left.total_seconds() < 300:  # Last 5 minutes
                    risk_score += 15
                    patterns.append("Last minute bidding")
            
            return {
                'type': 'PATTERN',
                'is_valid': risk_score < 30,
                'risk_score': risk_score,
                'warning': f"Suspicious patterns: {', '.join(patterns)}" if patterns else None,
                'details': {
                    'patterns_detected': patterns,
                    'time_left_seconds': time_left.total_seconds() if product.event_ends else None
                }
            }
            
        except Exception as e:
            logger.error(f"Error in pattern validation: {str(e)}")
            return None
    
    def _validate_account_age(self, user: User, profile: UserBehaviorProfile) -> Dict:
        """Validate account age and activity"""
        try:
            account_age = (timezone.now() - user.date_joined).days
            profile.account_age_days = account_age
            profile.save()
            
            risk_score = 0
            if account_age < 1:
                risk_score = 40
            elif account_age < 7:
                risk_score = 20
            elif account_age < 30:
                risk_score = 10
            
            return {
                'type': 'BEHAVIOR',
                'is_valid': True,
                'risk_score': risk_score,
                'details': {'account_age_days': account_age}
            }
            
        except Exception as e:
            logger.error(f"Error in account age validation: {str(e)}")
            return None
    
    def _validate_concurrent_bids(self, user: User, product: Product) -> Dict:
        """Check for concurrent bidding on multiple products"""
        try:
            now = timezone.now()
            recent_time = now - timedelta(minutes=5)
            
            concurrent_bids = Bidnow.objects.filter(
                user=user,
                created_at__gte=recent_time
            ).exclude(product=product).count()
            
            risk_score = 0
            if concurrent_bids > 3:
                risk_score = 20
            elif concurrent_bids > 1:
                risk_score = 10
            
            return {
                'type': 'BEHAVIOR',
                'is_valid': True,
                'risk_score': risk_score,
                'details': {'concurrent_bids': concurrent_bids}
            }
            
        except Exception as e:
            logger.error(f"Error in concurrent bids validation: {str(e)}")
            return None
    
    def _validate_ip_consistency(self, user: User, ip_address: str) -> Dict:
        """Check IP address consistency"""
        try:
            if not ip_address:
                return None
                
            # Get recent bids from same IP
            recent_bids = Bidnow.objects.filter(
                created_at__gte=timezone.now() - timedelta(hours=1)
            ).select_related('user')
            
            # Count unique users from same IP
            ip_users = set()
            for bid in recent_bids:
                # In a real implementation, you'd store IP addresses with bids
                # For now, we'll simulate this check
                pass
            
            risk_score = 0
            if len(ip_users) > 3:
                risk_score = 30
            
            return {
                'type': 'IP',
                'is_valid': True,
                'risk_score': risk_score,
                'details': {'unique_users_from_ip': len(ip_users)}
            }
            
        except Exception as e:
            logger.error(f"Error in IP validation: {str(e)}")
            return None
    
    def _validate_device_fingerprint(self, user: User, user_agent: str) -> Dict:
        """Validate device fingerprint"""
        try:
            if not user_agent:
                return None
                
            # Basic user agent analysis
            risk_score = 0
            warnings = []
            
            # Check for automated tools
            automated_indicators = ['bot', 'crawler', 'spider', 'scraper', 'automated']
            if any(indicator in user_agent.lower() for indicator in automated_indicators):
                risk_score = 50
                warnings.append("Automated tool detected")
            
            # Check for missing or suspicious user agent
            if len(user_agent) < 10:
                risk_score += 20
                warnings.append("Suspicious user agent")
            
            return {
                'type': 'DEVICE',
                'is_valid': risk_score < 40,
                'risk_score': risk_score,
                'warning': '; '.join(warnings) if warnings else None,
                'details': {'user_agent': user_agent}
            }
            
        except Exception as e:
            logger.error(f"Error in device validation: {str(e)}")
            return None
    
    def _calculate_bid_increment(self, current_bid: Decimal) -> Decimal:
        """Calculate appropriate bid increment based on current bid amount"""
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
    
    def _is_sequential_pattern(self, amounts: List[float]) -> bool:
        """Check if bid amounts follow a sequential pattern"""
        if len(amounts) < 3:
            return False
        
        # Check for arithmetic progression
        differences = [amounts[i] - amounts[i+1] for i in range(len(amounts)-1)]
        return len(set(differences)) == 1
    
    def _update_user_profile(self, user: User, profile: UserBehaviorProfile, 
                           bid_amount: Decimal, validation_result: Dict):
        """Update user behavior profile after bid validation"""
        try:
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
            profile.risk_score = validation_result['risk_score']
            
            # Flag user if risk is too high
            if validation_result['risk_score'] >= self.risk_thresholds['high']:
                profile.is_flagged = True
                profile.suspicious_activity_count += 1
            
            profile.save()
            
        except Exception as e:
            logger.error(f"Error updating user profile: {str(e)}")
    
    def _create_fraud_alert(self, user: User, product: Product, 
                          bid_amount: Decimal, validation_result: Dict):
        """Create fraud alert for high-risk activities"""
        try:
            severity = 'LOW'
            if validation_result['risk_score'] >= self.risk_thresholds['critical']:
                severity = 'CRITICAL'
            elif validation_result['risk_score'] >= self.risk_thresholds['high']:
                severity = 'HIGH'
            elif validation_result['risk_score'] >= self.risk_thresholds['medium']:
                severity = 'MEDIUM'
            
            description = f"High risk bid detected. Risk score: {validation_result['risk_score']:.1f}"
            if validation_result['warnings']:
                description += f" Warnings: {'; '.join(validation_result['warnings'])}"
            
            alert = FraudAlert.objects.create(
                user=user,
                product=product,
                alert_type='HIGH_RISK_BID',
                severity=severity,
                description=description,
                risk_score=validation_result['risk_score']
            )
            
            return alert
            
        except Exception as e:
            logger.error(f"Error creating fraud alert: {str(e)}")
            return None

class MLFraudDetector:
    """
    Machine Learning based fraud detection using scikit-learn
    """
    
    def __init__(self):
        self.model = IsolationForest(contamination=0.1, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
    
    def train_model(self):
        """Train the ML model on historical bid data"""
        try:
            # Get historical bid data
            bids = Bidnow.objects.select_related('user', 'product').all()
            
            if len(bids) < 100:  # Need sufficient data
                logger.warning("Insufficient data for ML training")
                return False
            
            # Prepare features
            features = []
            for bid in bids:
                feature_vector = self._extract_features(bid)
                if feature_vector:
                    features.append(feature_vector)
            
            if len(features) < 50:
                return False
            
            # Train the model
            X = np.array(features)
            X_scaled = self.scaler.fit_transform(X)
            self.model.fit(X_scaled)
            self.is_trained = True
            
            logger.info(f"ML model trained on {len(features)} samples")
            return True
            
        except Exception as e:
            logger.error(f"Error training ML model: {str(e)}")
            return False
    
    def predict_fraud(self, user: User, product: Product, bid_amount: Decimal) -> Dict:
        """Predict fraud probability using ML model"""
        try:
            if not self.is_trained:
                if not self.train_model():
                    return {'is_fraud': False, 'confidence': 0.0}
            
            # Create a mock bid for feature extraction
            mock_bid = type('MockBid', (), {
                'user': user,
                'product': product,
                'bid_amount': bid_amount,
                'created_at': timezone.now()
            })()
            
            features = self._extract_features(mock_bid)
            if not features:
                return {'is_fraud': False, 'confidence': 0.0}
            
            # Predict
            X = np.array([features])
            X_scaled = self.scaler.transform(X)
            prediction = self.model.predict(X_scaled)[0]
            score = self.model.score_samples(X_scaled)[0]
            
            # Convert to probability
            confidence = abs(score)
            is_fraud = prediction == -1
            
            return {
                'is_fraud': is_fraud,
                'confidence': min(confidence, 1.0),
                'anomaly_score': score
            }
            
        except Exception as e:
            logger.error(f"Error in ML prediction: {str(e)}")
            return {'is_fraud': False, 'confidence': 0.0}
    
    def _extract_features(self, bid) -> List[float]:
        """Extract features for ML model"""
        try:
            features = []
            
            # User features
            user = bid.user
            profile, _ = UserBehaviorProfile.objects.get_or_create(user=user)
            
            features.extend([
                profile.total_bids,
                profile.successful_bids,
                float(profile.average_bid_amount),
                profile.suspicious_activity_count,
                profile.account_age_days,
                float(bid.bid_amount),
            ])
            
            # Time features
            now = timezone.now()
            time_since_registration = (now - user.date_joined).total_seconds() / 86400  # days
            features.append(time_since_registration)
            
            # Product features
            product = bid.product
            features.extend([
                float(product.discounted_price),
                float(product.selling_price),
            ])
            
            # Bid timing features
            if product.event_ends:
                time_left = (product.event_ends - now).total_seconds()
                features.append(time_left)
            else:
                features.append(0)
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting features: {str(e)}")
            return []

# Global instances
fraud_detector = FraudDetectionEngine()
ml_detector = MLFraudDetector()
