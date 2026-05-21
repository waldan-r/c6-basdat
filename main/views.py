from django.shortcuts import render, redirect
import uuid
from django.contrib import messages
from .models import HasRelationship, Orders, Seat, Ticket, UserAccount, AccountRole, Customer, Organizer, Role, Artist, TicketCategory, Event
from django.db.models import Sum, Min, Q
from django.db import connection

# Helper function to convert raw SQL tuples into dictionaries
def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]

def login_view(request):
    if request.method == 'POST':
        username_input = request.POST.get('email')
        password_input = request.POST.get('password')

        with connection.cursor() as cursor:
            # validasi user
            cursor.execute("""
                SELECT user_id, username 
                FROM user_account 
                WHERE username = %s AND password = %s
            """, [username_input, password_input])
            
            user = cursor.fetchone()
            
            if user:
                user_id = str(user[0])
                username = user[1]
                
                # retrieve role
                cursor.execute("""
                    SELECT r.role_name 
                    FROM account_role ar
                    JOIN role r ON ar.role_id = r.role_id
                    WHERE ar.user_id = %s
                """, [user_id])
                
                role_row = cursor.fetchone()
                role_name = role_row[0] if role_row else 'GUEST'

                # save session
                request.session['user_id'] = user_id
                request.session['username'] = username
                request.session['role'] = role_name
                
                return redirect('dashboard')
            else:
                messages.error(request, "Email atau Password salah!")
                return redirect('login')

    return render(request, 'login.html')

def logout_view(request):
    request.session.flush()
    return redirect('login')

def register_view(request):
    if request.method == 'POST':
        role_choice = request.POST.get('role')
        username = request.POST.get('username')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        # basic validatin
        if password != confirm_password:
            messages.error(request, "Konfirmasi password tidak cocok!")
            return redirect('register')
        
        if len(password) < 6:
            messages.error(request, "Password minimal 6 karakter!")
            return redirect('register')

        with connection.cursor() as cursor:
            # check if username exists
            cursor.execute("SELECT 1 FROM user_account WHERE username = %s", [username])
            if cursor.fetchone():
                messages.error(request, "Username sudah terdaftar!")
                return redirect('register')

            # if username doesnt exist yet
            try:
                # create user_account
                user_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO user_account (user_id, username, password) 
                    VALUES (%s, %s, %s)
                """, [user_id, username, password])

                # role string -> DB role name
                role_map = {
                    'admin': 'ADMIN',
                    'customer': 'CUSTOMER',
                    'organizer': 'ORGANIZER'
                }
                target_role = role_map.get(role_choice)
                
                # fetch dynamic role_id dari DB
                cursor.execute("SELECT role_id FROM role WHERE role_name = %s", [target_role])
                role_row = cursor.fetchone()
                
                if role_row:
                    role_id = str(role_row[0])
                    # Simpan ke account_role
                    cursor.execute("""
                        INSERT INTO account_role (role_id, user_id) 
                        VALUES (%s, %s)
                    """, [role_id, user_id])

                # Simpan ke tabel customer / organizer
                if role_choice == 'customer':
                    customer_id = str(uuid.uuid4())
                    full_name = request.POST.get('full_name')
                    phone_number = request.POST.get('phone_number')
                    
                    cursor.execute("""
                        INSERT INTO customer (customer_id, full_name, phone_number, user_id) 
                        VALUES (%s, %s, %s, %s)
                    """, [customer_id, full_name, phone_number, user_id])
                    
                elif role_choice == 'organizer':
                    organizer_id = str(uuid.uuid4())
                    full_name = request.POST.get('full_name')
                    email = request.POST.get('email')
                    
                    cursor.execute("""
                        INSERT INTO organizer (organizer_id, organizer_name, contact_email, user_id) 
                        VALUES (%s, %s, %s, %s)
                    """, [organizer_id, full_name, email, user_id])

                messages.success(request, "Registrasi berhasil! Silakan login.")
                return redirect('login')

            except Exception as e:
                messages.error(request, f"Terjadi kesalahan: {str(e)}")
                return redirect('register')

    return render(request, 'register.html')

def dashboard_view(request):
    if 'user_id' not in request.session:
        return redirect('login')
        
    context = {
        'role': request.session.get('role', 'GUEST'),
        'username': request.session.get('username')
    }
    return render(request, 'dashboard.html', context)

def artist_list_view(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM artist")
        artists = dictfetchall(cursor)
        
    context = {
        'artists': artists,
        'role': request.session.get('role', 'GUEST')
    }
    return render(request, 'artists.html', context)

def artist_manage_view(request):
    if request.method == 'POST':
        action = request.POST.get('action')

        with connection.cursor() as cursor:
            # CREATE ARTIST
            if action == 'create':
                name = request.POST.get('name')
                genre = request.POST.get('genre', '')
                
                if not name:
                    messages.error(request, "Name wajib diisi!")
                else:
                    cursor.execute("""
                        INSERT INTO artist (artist_id, name, genre) 
                        VALUES (%s, %s, %s)
                    """, [str(uuid.uuid4()), name, genre])
                    messages.success(request, "Artist baru berhasil ditambahkan!")

            # UPDATE ARTIST
            elif action == 'update':
                artist_id = request.POST.get('artist_id')
                name = request.POST.get('name')
                genre = request.POST.get('genre', '')

                if not name:
                    messages.error(request, "Name wajib diisi!")
                else:
                    cursor.execute("""
                        UPDATE artist 
                        SET name = %s, genre = %s 
                        WHERE artist_id = %s
                    """, [name, genre, artist_id])
                    
                    if cursor.rowcount > 0:
                        messages.success(request, "Data artist berhasil diperbarui!")
                    else:
                        messages.error(request, "Data artist tidak ditemukan!")

            # DELETE ARTIST
            elif action == 'delete':
                artist_id = request.POST.get('artist_id')
                cursor.execute("DELETE FROM artist WHERE artist_id = %s", [artist_id])
                
                if cursor.rowcount > 0:
                    messages.success(request, "Artist berhasil dihapus!")
                else:
                    messages.error(request, "Data artist tidak ditemukan!")

        return redirect('artist_manage')

    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM artist")
        artists = dictfetchall(cursor)

    context = {
        'artists': artists,
        'role': request.session.get('role', 'GUEST')
    }
    return render(request, 'artist_manage.html', context)

def ticket_category_manage_view(request):
    role = request.session.get('role', 'GUEST')
    
    if request.method == 'POST':
        if role not in ['ADMIN', 'ORGANIZER']:
            messages.error(request, "Anda tidak memiliki akses untuk melakukan aksi ini.")
            return redirect('ticket_category_manage')

        action = request.POST.get('action')

        with connection.cursor() as cursor:
            # DELETE TICKET CATEGORY
            if action == 'delete':
                category_id = request.POST.get('category_id')
                # fetch name for message
                cursor.execute("SELECT category_name FROM ticket_category WHERE category_id = %s", [category_id])
                cat = cursor.fetchone()
                
                if cat:
                    cursor.execute("DELETE FROM ticket_category WHERE category_id = %s", [category_id])
                    messages.success(request, f"Kategori Tiket '{cat[0]}' berhasil dihapus!")
                else:
                    messages.error(request, "Data kategori tiket tidak ditemukan!")
                return redirect('ticket_category_manage')

            # inputs for CREATE + UPDATE
            category_name = request.POST.get('category_name')
            event_id = request.POST.get('event_id')
            
            try:
                quota = int(request.POST.get('quota'))
                price = float(request.POST.get('price'))
            except (ValueError, TypeError):
                messages.error(request, "Format Kuota atau Harga tidak valid!")
                return redirect('ticket_category_manage')

            if not category_name or not event_id:
                messages.error(request, "Seluruh field wajib diisi!")
                return redirect('ticket_category_manage')
            if quota <= 0:
                messages.error(request, "Kuota harus berupa bilangan bulat positif (> 0)!")
                return redirect('ticket_category_manage')
            if price < 0:
                messages.error(request, "Harga tidak boleh negatif (>= 0)!")
                return redirect('ticket_category_manage')

            # validasi event + venue capacity
            cursor.execute("""
                SELECT v.capacity 
                FROM event e
                JOIN venue v ON e.venue_id = v.venue_id
                WHERE e.event_id = %s
            """, [event_id])
            
            venue_row = cursor.fetchone()
            if not venue_row:
                messages.error(request, "Event tidak valid.")
                return redirect('ticket_category_manage')
                
            venue_capacity = venue_row[0]

            if action == 'create':
                cursor.execute("""
                    SELECT COALESCE(SUM(quota), 0) 
                    FROM ticket_category 
                    WHERE event_id = %s
                """, [event_id])
                current_total_quota = cursor.fetchone()[0]
                
                if current_total_quota + quota > venue_capacity:
                    messages.error(request, f"Gagal! Total kuota melebihi kapasitas venue ({venue_capacity} kursi).")
                else:
                    cursor.execute("""
                        INSERT INTO ticket_category (category_id, category_name, quota, price, event_id)
                        VALUES (%s, %s, %s, %s, %s)
                    """, [str(uuid.uuid4()), category_name, quota, price, event_id])
                    messages.success(request, "Kategori Tiket baru berhasil dibuat!")

            elif action == 'update':
                category_id = request.POST.get('category_id')
                
                cursor.execute("""
                    SELECT COALESCE(SUM(quota), 0) 
                    FROM ticket_category 
                    WHERE event_id = %s AND category_id != %s
                """, [event_id, category_id])
                
                other_categories_quota = cursor.fetchone()[0]
                
                if other_categories_quota + quota > venue_capacity:
                    messages.error(request, f"Gagal Update! Total kuota melebihi kapasitas venue ({venue_capacity} kursi).")
                else:
                    cursor.execute("""
                        UPDATE ticket_category 
                        SET category_name = %s, quota = %s, price = %s
                        WHERE category_id = %s
                    """, [category_name, quota, price, category_id])
                    
                    if cursor.rowcount > 0:
                        messages.success(request, "Data Kategori Tiket berhasil diperbarui!")
                    else:
                        messages.error(request, "Kategori tiket tidak ditemukan!")

        return redirect('ticket_category_manage')

    # prepare GET request
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT tc.*, e.event_title 
            FROM ticket_category tc
            JOIN event e ON tc.event_id = e.event_id
            ORDER BY e.event_title, tc.category_name
        """)
        categories = dictfetchall(cursor)
        
        cursor.execute("SELECT * FROM event")
        events = dictfetchall(cursor)
        
    context = {
        'categories': categories,
        'events': events,
        'role': role 
    }
    return render(request, 'ticket_category_manage.html', context)

def list_event(request):
    role = request.session.get('role', 'GUEST')
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action')

            with transaction.atomic(): 
                if action in ['CREATE', 'UPDATE']:
                    # Cari Venue berdasarkan nama yang dikirim dari modal
                    venue_obj = Venue.objects.get(venue_name=data.get('venue'))
                    
                    # Logika Create atau Update
                    event_id = data.get('event_id') if action == 'UPDATE' else str(uuid.uuid4())[:18]
                    
                    event, created = Event.objects.update_or_create(
                        event_id=event_id,
                        defaults={
                            'event_title': data.get('name'),
                            'event_datetime': f"{data.get('date')} {data.get('time')}",
                            'venue': venue_obj,
                            'organizer': Organizer.objects.first() 
                        }
                    )

                    # Simpan Kategori Tiket 
                    TicketCategory.objects.filter(event=event).delete()
                    for cat in data.get('categories', []):
                        TicketCategory.objects.create(
                            category_id=str(uuid.uuid4())[:18],
                            category_name=cat['name'],
                            price=cat['price'],
                            quota=cat['stock'],
                            event=event
                        )

            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    search_query = request.GET.get('q', '')
    venue_filter = request.GET.get('venue', '')
    artist_filter = request.GET.get('artist', '')

    events_qs = Event.objects.select_related('venue').prefetch_related('categories', 'eventartist_set__artist')

    if search_query:
        events_qs = events_qs.filter(event_title__icontains=search_query)
    if venue_filter:
        events_qs = events_qs.filter(venue_id=venue_filter)
    if artist_filter:
        events_qs = events_qs.filter(eventartist_set__artist_id=artist_filter)

    events_data = []
    for e in events_qs:
        cats = list(e.categories.values('category_name', 'price', 'quota'))
        min_p = e.categories.aggregate(Min('price'))['price__min'] or 0
        
        events_data.append({
            'id': e.event_id,
            'name': e.event_title,
            'date': e.event_datetime.strftime('%Y-%m-%d'),
            'time': e.event_datetime.strftime('%H:%M'),
            'venue': e.venue.venue_name,
            'categories': [{'name': c['category_name'], 'price': int(c['price']), 'stock': c['quota']} for c in cats],
            'min_price': int(min_p)
        })

    context = {
        'role': role,
        'events_js': json.dumps(events_data), 
        'venues': Venue.objects.all(),
        'artists': Artist.objects.all(),
    }
    return render(request, 'event.html', context)

def list_venue(request):
    role = request.session.get('role', 'GUEST')
    venues_qs = Venue.objects.all().order_by('venue_name')

    # Hitung Statistik Otomatis
    total_capacity = venues_qs.aggregate(Sum('capacity'))['capacity__sum'] or 0
    total_reserved = venues_qs.filter(has_reserved_seating=True).count()

    context = {
        'venues': venues_qs,
        'role': role,
        'stats': {
            'total_venue': venues_qs.count(),
            'total_reserved': total_reserved,
            'total_capacity': total_capacity,
        }
    }
    return render(request, 'venue.html', context)
    
def venue_manage_view(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        
        try:
            if action == 'CREATE':
                new_venue = Venue(
                    venue_id=str(uuid.uuid4())[:18],
                    venue_name=request.POST.get('nama'),
                    address=request.POST.get('alamat'),
                    city=request.POST.get('kota'),
                    capacity=int(request.POST.get('kapasitas')),
                    has_reserved_seating=request.POST.get('reserved') == 'on'
                )
                new_venue.save() # Ini akan memicu fungsi clean() di models
                messages.success(request, "Venue berhasil ditambahkan!")

            elif action == 'UPDATE':
                v_id = request.POST.get('venue_id')
                venue = Venue.objects.get(pk=v_id)
                venue.venue_name = request.POST.get('nama')
                venue.address = request.POST.get('alamat')
                venue.city = request.POST.get('kota')
                venue.capacity = int(request.POST.get('kapasitas'))
                venue.has_reserved_seating = request.POST.get('reserved') == 'on'
                venue.save()
                messages.success(request, "Data venue berhasil diperbarui!")

            elif action == 'DELETE':
                v_id = request.POST.get('venue_id')
                venue = Venue.objects.get(pk=v_id)
                venue.delete() # Ini akan memicu proteksi event aktif di models
                messages.success(request, "Venue berhasil dihapus!")

        except ValidationError as e:
            # Menangkap pesan error dari models.py (Duplikasi & Event Aktif)
            messages.error(request, e.message)
        except Exception as e:
            messages.error(request, f"Terjadi kesalahan: {str(e)}")

    return redirect('list_venue')

def ticket_view(request):
    role = request.session.get('role', 'GUEST')
    
    with connection.cursor() as cursor:
        # fetch records
        cursor.execute("SELECT * FROM ticket")
        tickets = dictfetchall(cursor)
        
        cursor.execute("SELECT * FROM ticket_category WHERE category_id IN (SELECT tcategory_id FROM ticket)")
        categories = dictfetchall(cursor)
        
        cursor.execute("SELECT * FROM event WHERE event_id IN (SELECT event_id FROM ticket_category)")
        events = dictfetchall(cursor)
        
        cursor.execute("SELECT * FROM orders WHERE order_id IN (SELECT torder_id FROM ticket)")
        order = dictfetchall(cursor)
        
        cursor.execute("SELECT * FROM customer WHERE customer_id IN (SELECT customer_id FROM orders)")
        pelanggan = dictfetchall(cursor)
        
        cursor.execute("""
            SELECT hr.ticket_id, s.*
            FROM has_relationship hr
            JOIN seat s ON hr.seat_id = s.seat_id
        """)
        seats = dictfetchall(cursor)

    context = {
        'tickets': tickets,
        'events': events,
        'categories': categories,
        'pelanggan': pelanggan,
        'order': order,
        'seats': seats
    }
    
    if role == 'CUSTOMER':
        return render(request, 'my_tickets.html', context)
    else:
        return render(request, 'ticket_manage.html', context)
    
def seats_view(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM seat")
        seats = dictfetchall(cursor)
    return render(request, 'seats.html', {'seats': seats})