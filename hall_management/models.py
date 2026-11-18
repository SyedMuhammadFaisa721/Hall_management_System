from django.db import models
from django.utils import timezone
from datetime import datetime
from decimal import Decimal

# START: Booking/payment method backend
PAYMENT_METHOD_CHOICES = [
    ('cash', 'Cash'),
    ('Bank Transfer', 'Bank transfer'),
    ('card', 'Card'),
    ('Online', 'Online'),
]
# END: Booking/payment method backend

class Hall_portion(models.Model):
     portion_name = models.CharField(max_length=10 , null=False)
     portion_capacity = models.PositiveBigIntegerField()
     portion_status = models.CharField(max_length=20 
                                       , choices=[('Active','Active'), ('Inactive','Inactive')], default='Active')
     def __str__(self):
         return f'Portion: {self.portion_name}'
class newbooking(models.Model):
    booking_id     = models.CharField(max_length=40 , primary_key=True, editable=False)
    created_at     = models.DateField(auto_now_add=True)
    customer_name  = models.CharField(max_length=100)
    phone_number   = models.CharField(max_length=12)
    nic_number     = models.CharField(max_length=15 , blank=True , default='NIC Not Provided')
    customer_email = models.EmailField()
    event_name     = models.CharField(max_length=100)
    event_type     = models.CharField(max_length=100)
    event_date     = models.DateField()
    event_guest    = models.IntegerField(null=False)
    event_hall     = models.ManyToManyField(Hall_portion , related_name='booked_halls')
    special_req    = models.CharField(max_length=500 , blank=True , default='No Special Requirements')
    hall_price     = models.IntegerField(null=False)
    status         = models.CharField(max_length=20)
    event_time     = models.CharField(max_length=8, 
                                      choices=[('Day','Day'), ('Night','Night')],
                                      default = 'Night')
    payment_status = models.CharField(max_length=20 , default="Pending")
    service = models.CharField(max_length=20 , choices= [('Table Service','Table Service'), ('Buffet Service','Buffet Service')], default='Buffet Service')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, blank=True, default='')
    # START: Booking advance amount backend
    advance_amount = models.PositiveIntegerField(blank=True, null=True)
    # END: Booking advance amount backend

    @property
    def recorded_payment_total(self):
        total = self.payments.exclude(refference_num='None').aggregate(
            total=models.Sum('amount'),
        )['total']
        return total or Decimal('0')

    @property
    def remaining_balance(self):
        balance = (
            Decimal(self.hall_price)
            - Decimal(self.advance_amount or 0)
            - self.recorded_payment_total
        )
        return max(balance, Decimal('0'))

    def save(self , *args ,**kwargs):
        if not self.booking_id:
            current_year = datetime.now().year
            last_booking = newbooking.objects.filter(
                booking_id__startswith = f'BK-{current_year}'
            ).order_by("-booking_id").first()
            if last_booking:
                last_number = int(
                    last_booking.booking_id.split("-")[-1]
                )
                new_number = last_number + 1
            else:
                new_number = 1
            self.booking_id = (
                f"BK-{current_year}-{new_number:03d}"
            )
        super().save(*args , **kwargs)
    def __str__(self):
        return self.booking_id

class expense(models.Model):
    expense_id      = models.CharField(max_length=10 , primary_key=True , editable=False)
    def save(self , *args ,**kwargs):
            if not self.expense_id:
                current_year = datetime.now().year
                last_booking = expense.objects.filter(
                    expense_id__startswith = f'EXP-{current_year}'
                ).order_by("-expense_id").first()
                if last_booking:
                    last_number = int(
                        last_booking.expense_id.split("-")[-1]
                    )
                    new_number = last_number + 1
                else:
                    new_number = 1
                self.expense_id = (
                    f"EXP-{current_year}-{new_number:03d}"
                )
            super().save(*args , **kwargs)
    expense_title   = models.CharField(max_length=100)
    expense_category= models.CharField(max_length=50)
    date            = models.DateField()
    amount          = models.IntegerField(null= False)
    paid_by         = models.CharField(max_length=30)
    status          = models.CharField(max_length=20)
    def __str__(self):
        return self.expense_id

class staff(models.Model):
    staff_id        = models.CharField(max_length=10 ,primary_key=True , editable=False)
    def save(self , *args ,**kwargs):
                if not self.staff_id:
                    last_booking = staff.objects.filter(
                        staff_id__startswith = f'ST-'
                    ).order_by("-staff_id").first()
                    if last_booking:
                        last_number = int(
                            last_booking.staff_id.split("-")[-1]
                        )
                        new_number = last_number + 1
                    else:
                        new_number = 1
                    self.staff_id = (
                        f"ST-{new_number:03d}"
                    )
                super().save(*args , **kwargs)
    staff_name      = models.CharField(max_length=40)
    staff_email     = models.EmailField(null = True)
    staff_number    = models.CharField(max_length=13)
    staff_role      = models.CharField(max_length=30)
    staff_nic_num   = models.CharField(max_length=16 , unique=True , null=False)
    staff_status    = models.CharField(max_length=10)
    staff_join_date = models.DateField(default=timezone.now)
    category        = models.CharField(max_length=20 , default='worker')
    Salary_status   = models.CharField(
        max_length=20,
        choices=[('Paid', 'Paid'), ('Unpaid', 'Unpaid')],
        default='Unpaid',
    )
    def __str__(self):
         return self.staff_id
class InventoryCategory(models.Model):
    category_name       = models.CharField(max_length=20)
    def __str__(self):
         return self.category_name
class Inventory(models.Model):
    inventory_name      = models.CharField(max_length=20)
    category            = models.ForeignKey(InventoryCategory , on_delete= models.CASCADE)
    inventory_quantity  = models.IntegerField()
    available_quantity  = models.IntegerField()
    damage_quantity     = models.IntegerField()
    def __str__(self):
         return self.inventory_name
class payment(models.Model):
     payment_id = models.CharField(max_length= 40 ,primary_key=True , editable=False)
     def save(self , *args ,**kwargs):
                          
                          if not self.payment_id:
                              current_year = datetime.now().year
                              current_day = datetime.today()
                              month_name = current_day.strftime('%b')
                              last_booking = payment.objects.filter(
                                  payment_id__startswith = f'PAY-{month_name}-{current_year}'
                              ).order_by("-payment_id").first()
                              if last_booking:
                                  last_number = int(
                                      last_booking.payment_id.split("-")[-1]
                                  )
                                  new_number = last_number + 1
                              else:
                                  new_number = 1
                              self.payment_id = (
                                  f"PAY-{month_name}-{current_year}-{new_number:03d}"
                              )
                          super().save(*args , **kwargs)
     booking = models.ForeignKey(newbooking , on_delete=models.CASCADE , related_name='payments')
     payment_date =  models.DateField(default=timezone.now )
     method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
     amount = models.DecimalField(max_digits=12 , decimal_places=2)
     refference_num = models.CharField(max_length=40)
     payment_status = models.CharField(max_length=30)
     created_at = models.DateTimeField(default = timezone.now ,editable= False)
     # START: Payment remaining amount calculation
     @property
     def remaining_amount(self):
          return self.amount - (self.booking.advance_amount or 0)
     # END: Payment remaining amount calculation
     def __str__(self):
          return self.payment_id    
# Create your models here.
