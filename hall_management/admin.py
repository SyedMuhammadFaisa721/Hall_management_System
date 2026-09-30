from django.contrib import admin
from .models import staff, newbooking , expense , InventoryCategory , Inventory
admin.site.register(newbooking)
admin.site.register(staff)
admin.site.register(expense)
admin.site.register(InventoryCategory)
admin.site.register(Inventory)

# Register your models here.
