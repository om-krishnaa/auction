# D:\auction\public_panel\models.py

from django.db import models

# Example model
class AuctionItem(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    starting_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
