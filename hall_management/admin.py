from django.contrib import admin
from .models import staff, newbooking , expense , InventoryCategory , Inventory , payment , Hall_portion
admin.site.register(newbooking)
admin.site.register(staff)
admin.site.register(expense)
admin.site.register(InventoryCategory)
admin.site.register(Inventory)
admin.site.register(payment)
admin.site.register(Hall_portion)

# Register your models here.
