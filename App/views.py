from django.shortcuts import render, redirect
from django.contrib import messages
from .models import AuctionItem

from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
import os

User = get_user_model()

def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            
            # Generate password reset token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Build password reset link
            reset_link = request.build_absolute_uri(
                f'/reset-password/{uid}/{token}/'
            )
            
            # Email content
            context = {
                'user': user,
                'reset_link': reset_link,
                'site_name': 'eAuction'
            }
            
            # Render email templates
            html_message = render_to_string('emails/password_reset_email.html', context)
            plain_message = strip_tags(html_message)
            
            # Send email
            try:
                send_mail(
                    subject='Reset Your Password - eAuction',
                    message=plain_message,
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[email],
                    html_message=html_message,
                    fail_silently=False,
                )
                messages.success(request, 'Password reset link has been sent to your email.')
            except Exception as e:
                messages.error(request, 'Failed to send email. Please try again later.')
                
        except User.DoesNotExist:
            # Don't reveal that the user doesn't exist
            messages.info(request, 'If an account exists with this email, you will receive password reset instructions.')
    
    return render(request, 'public_panel/forgot_password.html')

def reset_password_confirm(request, uidb64, token):
    try:
        # Decode the user id
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
        
        # Verify the token
        if default_token_generator.check_token(user, token):
            if request.method == 'POST':
                new_password = request.POST.get('new_password')
                confirm_password = request.POST.get('confirm_password')
                
                if new_password == confirm_password:
                    # Set new password
                    user.set_password(new_password)
                    user.save()
                    messages.success(request, 'Your password has been reset successfully. You can now login with your new password.')
                    return redirect('login')
                else:
                    messages.error(request, 'Passwords do not match.')
            
            return render(request, 'public_panel/reset_password_confirm.html')
        else:
            messages.error(request, 'The password reset link is invalid or has expired.')
            return redirect('forgot_password')
            
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        messages.error(request, 'The password reset link is invalid or has expired.')
        return redirect('forgot_password') 