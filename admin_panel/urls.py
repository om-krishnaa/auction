from django.urls import path
from .import views
from admin_panel.views import (
    index, admin_login_view, admin_register_view, addproduct, product_create, 
    product_update, product_list, product_delete,
    aboutus_list, aboutus_create, aboutus_update, aboutus_delete,
    aboutus_toggle_status, aboutus_reorder,
    sitesetting_list, sitesetting_create, sitesetting_update,
    all_users_view, logout_view, product_detail,
    export_bids_csv, contact_us, feedback, user_delete,
    fraud_dashboard, fraud_alerts_list, resolve_fraud_alert,
    user_risk_profiles, flag_user, bid_validation_log,
    auction_management, close_auction_manual, start_auction_manual,
    pause_auction_manual, extend_auction, auction_winners,
    mark_winner_paid, mark_winner_delivered
)

urlpatterns = [
    # Admin Dashboard
    path('admin', index, name='admin'),
    path('admin-login/', admin_login_view, name='admin_login'),
    path('admin-register/', admin_register_view, name='admin_register'),
    path('logout/', logout_view, name='logout'),
    
    # Product Management
    path('addproduct/', addproduct, name='addproduct'),
    path('product/', product_list, name="product-list"),
    path('product/create/', product_create, name="product-create"),
    path('product/create/<int:pk>', product_update, name="product-update"),
    path('product/delete/<int:pk>/', product_delete, name="product-delete"),
    path('product/<int:product_id>/', product_detail, name='product_detail'),
    
    # About Us Management
    path('aboutus/', aboutus_list, name='aboutus_list'),
    path('aboutus/create/', aboutus_create, name='aboutus_add'),
    path('aboutus/update/<int:pk>/', aboutus_update, name='aboutus_update'),
    path('aboutus/delete/<int:pk>/', aboutus_delete, name='aboutus_delete'),
    path('aboutus/toggle-status/<int:pk>/', aboutus_toggle_status, name='aboutus_toggle_status'),
    path('aboutus/reorder/', aboutus_reorder, name='aboutus_reorder'),
    
    # Site Settings
    path('sitesetting/', sitesetting_list, name='sitesetting_list'),
    path('sitesetting/add/', sitesetting_create, name='sitesetting_add'),
    path('sitesetting/<int:pk>/edit/', sitesetting_update, name='sitesetting_edit'),
    
    # User Management
    path('dashboard/users/', all_users_view, name='all_users'),
    path('users/delete/<int:pk>/', user_delete, name='user-delete'),
    
    # Reports and Feedback
    path('export/bids/', export_bids_csv, name='export_bids_csv'),
    path('feedback/', feedback, name='feedback'),
    path('contact/', contact_us, name='contact_us'),
    
    # Fraud Detection
    path('fraud/dashboard/', fraud_dashboard, name='fraud_dashboard'),
    path('fraud/alerts/', fraud_alerts_list, name='fraud_alerts_list'),
    path('fraud/alerts/<int:alert_id>/resolve/', resolve_fraud_alert, name='resolve_fraud_alert'),
    path('fraud/users/', user_risk_profiles, name='user_risk_profiles'),
    path('fraud/users/<int:user_id>/flag/', flag_user, name='flag_user'),
    path('fraud/validations/', bid_validation_log, name='bid_validation_log'),
    
    # Auction Management
    path('auctions/', auction_management, name='auction_management'),
    path('auctions/<int:product_id>/close/', close_auction_manual, name='close_auction_manual'),
    path('auctions/<int:product_id>/start/', start_auction_manual, name='start_auction_manual'),
    path('auctions/<int:product_id>/pause/', pause_auction_manual, name='pause_auction_manual'),
    path('auctions/<int:product_id>/extend/', extend_auction, name='extend_auction'),
    path('auctions/winners/', auction_winners, name='auction_winners'),
    path('auctions/winners/<int:winner_id>/paid/', mark_winner_paid, name='mark_winner_paid'),
    path('auctions/winners/<int:winner_id>/delivered/', mark_winner_delivered, name='mark_winner_delivered'),
]
