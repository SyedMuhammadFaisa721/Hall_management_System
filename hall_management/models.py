from django.db import models
from datetime import datetime

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
    nic_number     = models.CharField(max_length=15 , null=True)
    customer_email = models.EmailField()
    event_name     = models.CharField(max_length=100)
    event_type     = models.CharField(max_length=100)
    event_date     = models.DateField()
    event_guest    = models.IntegerField(null=False)
    event_hall     = models.ManyToManyField(Hall_portion , related_name='booked_halls')
    special_req    = models.CharField(max_length=500 , null= True)
    hall_price     = models.IntegerField(null=False)
    status         = models.CharField(max_length=20)
    event_time     = models.CharField(max_length=8, 
                                      choices=[('Day','Day'), ('Night','Night')],
                                      default = 'Night')
    payment_status = models.CharField(max_length=20 , default="Pending")
    service = models.CharField(max_length=20 , choices= [('Table Service','Table Service'), ('Buffet Service','Buffet Service')], default='Buffet Service')
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
    staff_join_date = models.DateField(default=datetime.now)
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
     payment_date =  models.DateField(default=datetime.now)
     method = models.CharField(max_length=20)
     amount = models.DecimalField(max_digits=12 , decimal_places=2)
     refference_num = models.CharField(max_length=40)
     payment_status = models.CharField(max_length=30)
     def __str__(self):
          return self.payment_id    
# Create your models here.
