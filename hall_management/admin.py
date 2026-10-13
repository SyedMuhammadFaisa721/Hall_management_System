from django.contrib import admin
from .models import staff, newbooking , expense , InventoryCategory , Inventory , payment
admin.site.register(newbooking)
admin.site.register(staff)
admin.site.register(expense)
admin.site.register(InventoryCategory)
admin.site.register(Inventory)
admin.site.register(payment)

# Register your models here.
