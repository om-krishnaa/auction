from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag
def get_category_icon(category):
    """Return the appropriate icon for a product category"""
    icon_map = {
        'E': 'electronics-icon',  # Electronics
        'F': 'fashion-icon',      # Fashion
        'H': 'home-icon',         # Home
        'S': 'sports-icon',       # Sports
        'B': 'books-icon',        # Books
        'V': 'vehicles-icon',     # Vehicles
    }
    
    icon_name = icon_map.get(category, 'electronics-icon')
    return mark_safe(f'<svg class="category-icon" width="20" height="20" viewBox="0 0 16 16"><use href="#{icon_name}"></use></svg>')

@register.simple_tag
def get_category_name(category):
    """Return the display name for a product category"""
    name_map = {
        'E': 'Electronics',
        'F': 'Fashion',
        'H': 'Home & Garden',
        'S': 'Sports',
        'B': 'Books',
        'V': 'Vehicles',
    }
    
    return name_map.get(category, 'Other')

@register.simple_tag
def get_user_avatar(user, size='sm'):
    """Return user avatar with fallback to placeholder"""
    if hasattr(user, 'profile') and user.profile.avatar:
        return user.profile.avatar.url
    
    # Return a colored avatar based on username
    colors = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe', '#00f2fe', '#56ab2f', '#a8e6cf']
    color_index = hash(user.username) % len(colors)
    color = colors[color_index]
    
    size_map = {
        'sm': '32',
        'md': '48',
        'lg': '64'
    }
    
    avatar_size = size_map.get(size, '32')
    initial = user.username[0].upper()
    
    return mark_safe(f'''
        <div class="avatar avatar-{size}" style="background-color: {color}; width: {avatar_size}px; height: {avatar_size}px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-weight: 600;">
            {initial}
        </div>
    ''')

@register.filter
def format_currency(amount):
    """Format amount as currency"""
    return f"Rs. {amount:,.0f}"

@register.simple_tag
def format_currency_tag(amount):
    """Format amount as currency (template tag version)"""
    return f"Rs. {amount:,.0f}"

@register.filter
def time_remaining(end_time):
    """Calculate and format time remaining"""
    from django.utils import timezone
    from datetime import timedelta
    
    now = timezone.now()
    if end_time <= now:
        return "Ended"
    
    delta = end_time - now
    total_seconds = int(delta.total_seconds())
    
    if total_seconds < 3600:  # Less than 1 hour
        minutes = total_seconds // 60
        return f"{minutes}m"
    elif total_seconds < 86400:  # Less than 1 day
        hours = total_seconds // 3600
        return f"{hours}h"
    else:  # More than 1 day
        days = total_seconds // 86400
        return f"{days}d"
