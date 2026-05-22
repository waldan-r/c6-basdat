from django.http import HttpRequest
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import connection
from django.urls import reverse
from urllib.parse import urlencode
import json
import uuid

# Helper function to convert raw SQL tuples into dictionaries
def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


def db_cursor():
    cursor = connection.cursor()
    cursor.execute("SET search_path TO tiktaktuk, public")
    return cursor


def is_uuid(value):
    try:
        uuid.UUID(str(value))
    except (TypeError, ValueError):
        return False
    return True

def login_view(request):
    if request.method == 'POST':
        username_input = request.POST.get('email')
        password_input = request.POST.get('password')

        with db_cursor() as cursor:
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

    return render(request, "login.html")


def logout_view(request):
    request.session.flush()
    return redirect("login")


def register_view(request):
    if request.method == 'POST':
        role_choice = request.POST.get('role')
        username = request.POST.get('username')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        # basic validatin
        if password != confirm_password:
            messages.error(request, "Konfirmasi password tidak cocok!")
            return redirect("register")
        if len(password) < 6:
            messages.error(request, "Password minimal 6 karakter!")
            return redirect('register')

        with db_cursor() as cursor:
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

    return render(request, "register.html")


def dashboard_view(request):
    if "user_id" not in request.session:
        return redirect("login")
    return render(
        request,
        "dashboard.html",
        {"role": request.session.get("role", "GUEST"), "username": request.session.get("username")},
    )


def artist_list_view(request):
    with db_cursor() as cursor:
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

        with db_cursor() as cursor:
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

    with db_cursor() as cursor:
        cursor.execute("SELECT * FROM artist")
        artists = dictfetchall(cursor)

    context = {
        'artists': artists,
        'role': request.session.get('role', 'GUEST')
    }
    return render(request, 'artist_manage.html', context)

def ticket_category_manage_view(request):
    role = request.session.get("role", "GUEST")

    if request.method == "POST":
        if role not in ["ADMIN", "ORGANIZER"]:
            messages.error(request, "Anda tidak memiliki akses untuk melakukan aksi ini.")
            return redirect("ticket_category_manage")

        action = request.POST.get('action')

        with db_cursor() as cursor:
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
    with db_cursor() as cursor:
        cursor.execute("""
            SELECT tc.*, e.event_title
            FROM ticket_category tc
            JOIN event e ON tc.event_id = e.event_id
            ORDER BY e.event_title, tc.category_name
        """)
        categories = dictfetchall(cursor)
        
        cursor.execute("""
            SELECT e.event_id, e.event_title, v.capacity
            FROM event e
            JOIN venue v ON v.venue_id = e.venue_id
            ORDER BY e.event_title
        """)
        events = dictfetchall(cursor)
        
    context = {
        'categories': categories,
        'events': events,
        'role': role 
    }
    return render(request, 'ticket_category_manage.html', context)

def list_event(request):
    role = request.session.get('role', 'ADMIN')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            print("Membuat event baru...")
        elif action == 'update':
            print(f"Mengupdate event ID: {request.POST.get('event_id')}")
        
        return redirect('list_event')

    search = (request.GET.get("q") or "").strip()
    venue_filter = request.GET.get("venue")
    artist_filter = request.GET.get("artist")

    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT venue_id AS id, venue_name AS name, city
            FROM venue
            ORDER BY venue_name
            """
        )
        venues = dictfetchall(cursor)

        cursor.execute("SELECT artist_id AS id, name FROM artist ORDER BY name")
        artists = dictfetchall(cursor)

        conditions = []
        params = []
        if search:
            conditions.append("e.event_title ILIKE %s")
            params.append(f"%{search}%")
        if is_uuid(venue_filter):
            conditions.append("e.venue_id = %s")
            params.append(venue_filter)
        if is_uuid(artist_filter):
            conditions.append(
                """
                EXISTS (
                    SELECT 1
                    FROM event_artist ea_filter
                    WHERE ea_filter.event_id = e.event_id
                      AND ea_filter.artist_id = %s
                )
                """
            )
            params.append(artist_filter)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        cursor.execute(
            f"""
            SELECT e.event_id, e.event_title, e.event_datetime,
                   v.venue_name, v.city,
                   COALESCE(MIN(tc.price), 0) AS min_price,
                   COALESCE(string_agg(DISTINCT a.name, ', '), '') AS artist_names
            FROM event e
            JOIN venue v ON v.venue_id = e.venue_id
            LEFT JOIN event_artist ea ON ea.event_id = e.event_id
            LEFT JOIN artist a ON a.artist_id = ea.artist_id
            LEFT JOIN ticket_category tc ON tc.event_id = e.event_id
            {where_clause}
            GROUP BY e.event_id, e.event_title, e.event_datetime, v.venue_name, v.city
            ORDER BY e.event_datetime
            """,
            params,
        )
        event_rows = dictfetchall(cursor)

        event_ids = [str(event["event_id"]) for event in event_rows]
        categories_by_event = {event_id: [] for event_id in event_ids}
        if event_ids:
            cursor.execute(
                """
                SELECT event_id::text AS event_id, category_name, price, quota
                FROM ticket_category
                WHERE event_id::text = ANY(%s)
                ORDER BY price, category_name
                """,
                [event_ids],
            )
            for category in dictfetchall(cursor):
                categories_by_event[category["event_id"]].append(
                    {
                        "name": category["category_name"],
                        "price": int(category["price"] or 0),
                        "stock": category["quota"],
                    }
                )

    events = []
    for event in event_rows:
        event_id = str(event["event_id"])
        event_datetime = event["event_datetime"]
        categories = categories_by_event.get(event_id) or [
            {"name": "Belum ada kategori", "price": 0, "stock": 0}
        ]
        events.append(
            {
                "id": event_id,
                "name": event["event_title"],
                "date": event_datetime.date().isoformat(),
                "time": event_datetime.strftime("%H:%M"),
                "venue": event["venue_name"],
                "city": event["city"],
                "artists_list": [
                    name.strip()
                    for name in (event["artist_names"] or "").split(",")
                    if name.strip()
                ],
                "min_price": int(event["min_price"] or 0),
                "categories": categories,
                "poster": {
                    "url": "https://images.unsplash.com/photo-1459749411177-042180ce673c?auto=format&fit=crop&w=800"
                },
            }
        )

    context = {
        'role': role,
        'events': events,
        'events_json': json.dumps(events),
        'venues': venues,
        'artists': artists,
    }
    
    return render(request, 'event.html', context)

def list_venue(request):
    role = request.session.get('role', 'GUEST')

    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT v.venue_id, v.venue_name, v.capacity, v.address, v.city,
                   EXISTS (
                       SELECT 1
                       FROM seat s
                       WHERE s.venue_id = v.venue_id
                   ) AS has_reserved
            FROM venue v
            ORDER BY v.venue_name
            """
        )
        venues = dictfetchall(cursor)
    
    context = {
        'venues': venues,
        'role': role
    }
    return render(request, 'venue.html', context)
    
def placeholder(request, *args, **kwargs):
    return render(request, 'venue.html')

def venues(request):
    if request.method == "POST":
        action = request.POST.get("action")
        
        if action == "CREATE":
            pass
        elif action == "UPDATE":
            venue_id = request.POST.get("venue_id")
            pass
        elif action == "DELETE":
            venue_id = request.POST.get("venue_id")
            pass
            
        return redirect('venues') 

    with db_cursor() as cursor:
        cursor.execute("SELECT * FROM venue")
        venues_list = dictfetchall(cursor)

    return render(
        request,
        'venue.html',
        {'venues': venues_list, 'role': request.session.get('role', 'GUEST')},
    )

def ticket_view(request: HttpRequest):
    role = request.session.get('role', 'GUEST')
    user_id = request.session.get('user_id', '0')
    
    if role == 'GUEST': 
        return redirect("login")

    if request.method == "POST":
        action = request.POST.get('action')
        
        filter_params = {}
        if request.POST.get('ticket_filter'):
            filter_params['ticket_filter'] = request.POST.get('ticket_filter')
        if request.POST.get('ticket_status'):
            filter_params['ticket_status'] = request.POST.get('ticket_status')
            
        redirect_url = reverse('tickets')
        if filter_params:
            redirect_url += '?' + urlencode(filter_params)
        
        with db_cursor() as cursor:
            if action == 'create' and role in ['ADMIN', 'ORGANIZER']:
                order_id = request.POST.get('order_id')
                category_id = request.POST.get('category_id')
                seat_id = request.POST.get('seat_id')

                ticket_id = uuid.uuid4()
                # TODO: kode tiket gen
                ticket_code = f"TICK-{uuid.uuid4().hex[:8].upper()}"

                cursor.execute(
                    "insert into ticket (ticket_id, ticket_code, tcategory_id, torder_id) values (%s, %s, %s, %s) returning ticket_id",
                    [ticket_id, ticket_code, category_id, order_id]
                )
                new_ticket = cursor.fetchone()
                
                if new_ticket and seat_id:
                    new_ticket_id = new_ticket[0]
                    cursor.execute(
                        "insert into has_relationship (ticket_id, seat_id) values (%s, %s)",
                        [new_ticket_id, seat_id]
                    )
                
                return redirect(redirect_url)

            elif action == 'update' and role == 'ADMIN':
                ticket_id = request.POST.get('ticket_id')
                payment_status = request.POST.get('payment_status')
                seat_id = request.POST.get('seat_id')

                cursor.execute(
                    "update orders set payment_status = %s where order_id = (select torder_id from ticket where ticket_id = %s)",
                    [payment_status, ticket_id]
                )

                if seat_id:
                    cursor.execute("select 1 from has_relationship where ticket_id = %s", [ticket_id])
                    exists = cursor.fetchone()
                    
                    if exists:
                        cursor.execute(
                            "update has_relationship set seat_id = %s where ticket_id = %s",
                            [seat_id, ticket_id]
                        )
                    else:
                        cursor.execute(
                            "insert into has_relationship (ticket_id, seat_id) values (%s, %s)",
                            [ticket_id, seat_id]
                        )
                else:
                    cursor.execute("delete from has_relationship where ticket_id = %s", [ticket_id])

                return redirect(redirect_url)

            elif action == 'delete' and role == 'ADMIN':
                ticket_id = request.POST.get('ticket_id')

                cursor.execute("delete from has_relationship where ticket_id = %s", [ticket_id])
                
                cursor.execute("delete from ticket where ticket_id = %s", [ticket_id])

                return redirect(redirect_url)

        return redirect(redirect_url)

    with db_cursor() as cursor:
        if request.method == "GET":
            ticket_filter = (request.GET.get('ticket_filter') or '').strip()
            status_filter = (request.GET.get('ticket_status') or '').strip()

            base_query = """
                select
                    t.ticket_id, t.ticket_code, t.tcategory_id, t.torder_id,
                    tc.category_id, tc.category_name, tc.price, tc.quota,
                    e.event_id, e.event_title, e.organizer_id,
                    o.order_id, o.order_date, o.payment_status, o.total_amount,
                    c.customer_id, c.full_name, c.user_id as customer_user_id,
                    hr.seat_id,
                    s.section, s.seat_number, s.row_number
                from ticket t
                join ticket_category tc on tc.category_id = t.tcategory_id
                join event e on e.event_id = tc.event_id
                join orders o on o.order_id = t.torder_id
                join customer c on c.customer_id = o.customer_id
                left join has_relationship hr on hr.ticket_id = t.ticket_id
                left join seat s on s.seat_id = hr.seat_id
            """

            conditions = []
            params = []
            
            if role == 'CUSTOMER':
                conditions.append("c.user_id = %s")
                params.append(user_id)
            elif role == 'ORGANIZER':
                conditions.append("e.organizer_id = (select organizer_id from organizer where user_id = %s)")
                params.append(user_id)

            if ticket_filter:
                conditions.append("(lower(e.event_title) like lower(%s) or lower(t.ticket_code) like lower(%s))")
                params.append(f"%{ticket_filter}%")
                params.append(f"%{ticket_filter}%")

            if status_filter:
                conditions.append("o.payment_status = %s")
                params.append(status_filter)

            if conditions:
                base_query += " where " + " and ".join(conditions)
            
            cursor.execute(base_query, params)
            # print(cursor.description)
            tickets = dictfetchall(cursor)

            statuses = ["PENDING", "PAID", "CANCELLED"]

            orders_options = []
            events_options = []
            categories_options = []
            seats_options = []
            
            if role in ('ADMIN', 'ORGANIZER'):
                cursor.execute(
                    """
                    select o.order_id, o.order_date, o.payment_status, o.total_amount,
                           c.customer_id, c.full_name
                    from orders o
                    join customer c on c.customer_id = o.customer_id
                    order by o.order_date desc
                    """
                )
                orders_options = dictfetchall(cursor)

                if role == 'ORGANIZER':
                    cursor.execute(
                        """
                        select e.*
                        from event e
                        join organizer o on o.organizer_id = e.organizer_id
                        where o.user_id = %s
                        order by e.event_datetime
                        """,
                        [user_id],
                    )
                else:
                    cursor.execute("select * from event order by event_datetime")
                events_options = dictfetchall(cursor)

                category_params = []
                category_where = ""
                if role == 'ORGANIZER':
                    category_where = "where e.organizer_id = (select organizer_id from organizer where user_id = %s)"
                    category_params.append(user_id)
                cursor.execute(
                    f"""
                    select
                        tc.category_id,
                        tc.category_name,
                        e.event_title,
                        tc.event_id,
                        tc.price as harga,
                        tc.quota,
                        coalesce(count(t.ticket_id), 0) as terpakai
                    from ticket_category tc
                    join event e on tc.event_id = e.event_id
                    left join ticket t on tc.category_id = t.tcategory_id
                    {category_where}
                    group by tc.category_id, tc.category_name, e.event_title, tc.event_id, tc.price, tc.quota
                    having coalesce(count(t.ticket_id), 0) < tc.quota
                    order by e.event_title, tc.price
                    """,
                    category_params,
                )
                categories_options = dictfetchall(cursor)

                seat_params = []
                seat_where = ""
                if role == 'ORGANIZER':
                    seat_where = "where e.organizer_id = (select organizer_id from organizer where user_id = %s)"
                    seat_params.append(user_id)
                cursor.execute(
                    f"""
                    select s.seat_id, s.section, s.seat_number, s.row_number, s.venue_id,
                           e.event_id,
                        (select hr.ticket_id
                         from has_relationship hr
                         join ticket t on hr.ticket_id = t.ticket_id
                         join ticket_category tc on t.tcategory_id = tc.category_id
                         where hr.seat_id = s.seat_id and tc.event_id = e.event_id
                         limit 1) as occupied_by_ticket_id
                    from seat s
                    join event e on s.venue_id = e.venue_id
                    {seat_where}
                    order by s.section, s.row_number, s.seat_number
                    """,
                    seat_params,
                )
                seats_options = dictfetchall(cursor)

            context = {
                'tickets': tickets,
                'statuses': statuses,
                'orders_options': orders_options,
                'events_options': events_options,
                'categories_options': categories_options,
                'seats_options': seats_options,
                'event_filter': ticket_filter,
                'status_filter': status_filter,
                'role': role
            }
            return render(request, 'tickets.html', context)
    
def seats_view(request):
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT s.*, v.venue_name
            FROM seat s
            JOIN venue v ON v.venue_id = s.venue_id
            ORDER BY v.venue_name, s.section, s.row_number, s.seat_number
            """
        )
        seats = dictfetchall(cursor)
    return render(request, 'seats.html', {'seats': seats})
