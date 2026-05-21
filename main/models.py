from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

class UserAccount(models.Model):
    user_id = models.CharField(max_length=255, primary_key=True) #
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=255)

    class Meta:
        db_table = 'user_account'
        managed = False

class Role(models.Model):
    role_id = models.CharField(max_length=255, primary_key=True)
    role_name = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = 'role'
        managed = False

class AccountRole(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, db_column='role_id')
    user = models.ForeignKey(UserAccount, on_delete=models.CASCADE, db_column='user_id')

    class Meta:
        db_table = 'account_role'
        managed = False
        unique_together = (('role', 'user'),)

class Customer(models.Model):
    customer_id = models.CharField(max_length=255, primary_key=True)
    full_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    user = models.OneToOneField(UserAccount, on_delete=models.CASCADE, db_column='user_id')

    class Meta:
        db_table = 'customer'
        managed = False

class Organizer(models.Model):
    organizer_id = models.CharField(max_length=255, primary_key=True)
    organizer_name = models.CharField(max_length=100)
    contact_email = models.CharField(max_length=100, null=True, blank=True)
    user = models.OneToOneField(UserAccount, on_delete=models.CASCADE, db_column='user_id')

    class Meta:
        db_table = 'organizer'
        managed = False

class Venue(models.Model):
    venue_id = models.CharField(max_length=255, primary_key=True)
    venue_name = models.CharField(max_length=100)
    capacity = models.IntegerField()
    address = models.TextField()
    city = models.CharField(max_length=100)

    class Meta:
        db_table = 'venue'
        managed = False

    def clean(self):
        duplicates = Venue.objects.filter(
            venue_name__iexact=self.venue_name,
            city__iexact=self.city
        ).exclude(pk=self.venue_id)
        
        if duplicates.exists():
            existing = duplicates.first()
            raise ValidationError(
                f"ERROR: Venue \"{self.venue_name}\" di kota \"{self.city}\" sudah terdaftar dengan ID {existing.pk}."
            )

    def delete(self, *args, **kwargs):
        now = timezone.now()
        active_events = Event.objects.filter(
            venue=self,
            event_datetime__gte=now
        )
        
        if active_events.exists():
            raise ValidationError(
                f"ERROR: Venue '{self.venue_name}' masih memiliki event aktif sehingga tidak dapat dihapus."
            )
        super().delete(*args, **kwargs)
    
    @property
    def has_reserved_seating(self):
        return self.capacity % 2 == 0

class Event(models.Model):
    event_id = models.CharField(max_length=255, primary_key=True)
    event_datetime = models.DateTimeField()
    event_title = models.CharField(max_length=200)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, db_column='venue_id')
    organizer = models.ForeignKey(Organizer, on_delete=models.CASCADE, db_column='organizer_id')

    class Meta:
        db_table = 'event'
        managed = False

class Artist(models.Model):
    artist_id = models.CharField(max_length=255, primary_key=True)
    name = models.CharField(max_length=100)
    genre = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'artist'
        managed = False

class EventArtist(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, db_column='event_id')
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, db_column='artist_id')
    role = models.CharField(max_length=100)

    class Meta:
        db_table = 'event_artist'
        managed = False
        unique_together = (('event', 'artist'),)

class Seat(models.Model):
    seat_id = models.CharField(max_length=255, primary_key=True)
    section = models.CharField(max_length=50)
    seat_number = models.CharField(max_length=10)
    row_number = models.CharField(max_length=10)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, db_column='venue_id')

    class Meta:
        db_table = 'seat'
        managed = False

class TicketCategory(models.Model):
    category_id = models.CharField(max_length=255, primary_key=True)
    category_name = models.CharField(max_length=50)
    quota = models.IntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, db_column='event_id')

    class Meta:
        db_table = 'ticket_category'
        managed = False

class Orders(models.Model):
    order_id = models.CharField(max_length=255, primary_key=True)
    order_date = models.DateTimeField()
    payment_status = models.CharField(max_length=20)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, db_column='customer_id')

    class Meta:
        db_table = 'orders'
        managed = False

class Ticket(models.Model):
    ticket_id = models.CharField(max_length=255, primary_key=True)
    ticket_code = models.CharField(max_length=100, unique=True)
    tcategory = models.ForeignKey(TicketCategory, on_delete=models.CASCADE, db_column='tcategory_id')
    torder = models.ForeignKey(Orders, on_delete=models.CASCADE, db_column='torder_id')

    class Meta:
        db_table = 'ticket'
        managed = False

class HasRelationship(models.Model):
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE, db_column='seat_id')
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, db_column='ticket_id')

    class Meta:
        db_table = 'has_relationship'
        managed = False
        unique_together = (('seat', 'ticket'),)

class Promotion(models.Model):
    promotion_id = models.CharField(max_length=255, primary_key=True)
    promo_code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=20)
    discount_value = models.DecimalField(max_digits=12, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()
    usage_limit = models.IntegerField()

    class Meta:
        db_table = 'promotion'
        managed = False

class OrderPromotion(models.Model):
    order_promotion_id = models.CharField(max_length=255, primary_key=True)
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE, db_column='promotion_id')
    order = models.ForeignKey(Orders, on_delete=models.CASCADE, db_column='order_id')

    class Meta:
        db_table = 'order_promotion'
        managed = False