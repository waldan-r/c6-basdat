import json
import uuid
from decimal import Decimal
from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import DatabaseError, connection, transaction
from django.db.models import Min, Q, Sum
from django.http import HttpRequest, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse

# Import model lokal
from .models import (
    AccountRole,
    Artist,
    Customer,
    Event,
    EventArtist,
    HasRelationship,
    Orders,
    Organizer,
    Role,
    Seat,
    Ticket,
    TicketCategory,
    UserAccount,
    Venue,
)

def fetchall(cursor):
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def fetchone(cursor):
    row = cursor.fetchone()
    if row is None:
        return None
    columns = [column[0] for column in cursor.description]
    return dict(zip(columns, row))


def db_cursor():
    cursor = connection.cursor()
    cursor.execute("SET search_path TO tiktaktuk, public")
    return cursor


def money(value):
    return f"{Decimal(value or 0):,.0f}".replace(",", ".")


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("email")
        password = request.POST.get("password")

        with db_cursor() as cursor:
            cursor.execute(
                """
                SELECT ua.user_id, ua.username, COALESCE(r.role_name, 'GUEST') AS role_name
                FROM user_account ua
                LEFT JOIN account_role ar ON ar.user_id = ua.user_id
                LEFT JOIN role r ON r.role_id = ar.role_id
                WHERE ua.username = %s AND ua.password = %s
                LIMIT 1
                """,
                [username, password],
            )
            user = fetchone(cursor)

        if user is None:
            messages.error(request, "Email atau Password salah!")
            return redirect("login")

        request.session["user_id"] = str(user["user_id"])
        request.session["username"] = user["username"]
        request.session["role"] = user["role_name"]
        return redirect("dashboard")

    return render(request, "login.html")


def logout_view(request):
    request.session.flush()
    return redirect("login")


def register_view(request):
    if request.method == "POST":
        role_choice = request.POST.get("role")
        username = request.POST.get("username")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            messages.error(request, "Konfirmasi password tidak cocok!")
            return redirect("register")
        if len(password) < 6:
            messages.error(request, "Password minimal 6 karakter!")
            return redirect("register")

        role_name = {"admin": "ADMIN", "customer": "CUSTOMER", "organizer": "ORGANIZER"}.get(role_choice)
        if role_name is None:
            messages.error(request, "Role tidak valid!")
            return redirect("register")

        try:
            with transaction.atomic():
                with db_cursor() as cursor:
                    cursor.execute("SELECT 1 FROM user_account WHERE username = %s", [username])
                    if cursor.fetchone():
                        messages.error(request, "Username sudah terdaftar!")
                        return redirect("register")

                    cursor.execute("SELECT role_id FROM role WHERE role_name = %s", [role_name])
                    role = fetchone(cursor)
                    if role is None:
                        messages.error(request, "Role tidak ditemukan di database.")
                        return redirect("register")

                    user_id = str(uuid.uuid4())
                    cursor.execute(
                        "INSERT INTO user_account (user_id, username, password) VALUES (%s, %s, %s)",
                        [user_id, username, password],
                    )
                    cursor.execute(
                        "INSERT INTO account_role (role_id, user_id) VALUES (%s, %s)",
                        [role["role_id"], user_id],
                    )

                    if role_choice == "customer":
                        cursor.execute(
                            """
                            INSERT INTO customer (customer_id, full_name, phone_number, user_id)
                            VALUES (%s, %s, %s, %s)
                            """,
                            [
                                str(uuid.uuid4()),
                                request.POST.get("full_name"),
                                request.POST.get("phone_number"),
                                user_id,
                            ],
                        )
                    elif role_choice == "organizer":
                        cursor.execute(
                            """
                            INSERT INTO organizer (organizer_id, organizer_name, contact_email, user_id)
                            VALUES (%s, %s, %s, %s)
                            """,
                            [
                                str(uuid.uuid4()),
                                request.POST.get("full_name"),
                                request.POST.get("email") or username,
                                user_id,
                            ],
                        )

            messages.success(request, "Registrasi berhasil! Silakan login.")
            return redirect("login")
        except DatabaseError as exc:
            messages.error(request, f"Terjadi kesalahan: {exc}")
            return redirect("register")

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
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM artist")
        artists = dictfetchall(cursor)
        
    context = {
        'artists': artists,
        'role': request.session.get('role', 'GUEST')
    }
    return render(request, 'artists.html', context)

def artist_manage_view(request):
    if request.method == "POST":
        action = request.POST.get("action")
        artist_id = request.POST.get("artist_id")
        name = request.POST.get("name")
        genre = request.POST.get("genre", "")

        with db_cursor() as cursor:
            if action == "create":
                if not name:
                    messages.error(request, "Name wajib diisi!")
                else:
                    cursor.execute(
                        "INSERT INTO artist (artist_id, name, genre) VALUES (%s, %s, %s)",
                        [str(uuid.uuid4()), name, genre],
                    )
                    messages.success(request, "Artist baru berhasil ditambahkan!")
            elif action == "update":
                if not name:
                    messages.error(request, "Name wajib diisi!")
                else:
                    cursor.execute(
                        "UPDATE artist SET name = %s, genre = %s WHERE artist_id = %s",
                        [name, genre, artist_id],
                    )
                    messages.success(request, "Data artist berhasil diperbarui!")
            elif action == "delete":
                cursor.execute("DELETE FROM artist WHERE artist_id = %s", [artist_id])
                messages.success(request, "Artist berhasil dihapus!")

        return redirect("artist_manage")

    with db_cursor() as cursor:
        cursor.execute("SELECT artist_id, name, genre FROM artist ORDER BY name")
        artists = fetchall(cursor)
    return render(request, "artist_manage.html", {"artists": artists, "role": request.session.get("role", "GUEST")})

def ticket_category_manage_view(request):
    role = request.session.get("role", "GUEST")

    if request.method == "POST":
        if role not in ["ADMIN", "ORGANIZER"]:
            messages.error(request, "Anda tidak memiliki akses untuk melakukan aksi ini.")
            return redirect("ticket_category_manage")

        action = request.POST.get("action")
        category_id = request.POST.get("category_id")

        try:
            with db_cursor() as cursor:
                if action == "delete":
                    cursor.execute("DELETE FROM ticket_category WHERE category_id = %s", [category_id])
                    messages.success(request, "Kategori tiket berhasil dihapus!")
                    return redirect("ticket_category_manage")

                category_name = request.POST.get("category_name")
                event_id = request.POST.get("event_id")
                quota = int(request.POST.get("quota"))
                price = Decimal(request.POST.get("price"))

                if not category_name or not event_id:
                    messages.error(request, "Seluruh field wajib diisi!")
                    return redirect("ticket_category_manage")
                if quota <= 0:
                    messages.error(request, "Kuota harus berupa bilangan bulat positif (> 0)!")
                    return redirect("ticket_category_manage")
                if price < 0:
                    messages.error(request, "Harga tidak boleh negatif (>= 0)!")
                    return redirect("ticket_category_manage")

                cursor.execute(
                    """
                    SELECT e.event_id, v.capacity
                    FROM event e
                    JOIN venue v ON v.venue_id = e.venue_id
                    WHERE e.event_id = %s
                    """,
                    [event_id],
                )
                event = fetchone(cursor)
                if event is None:
                    messages.error(request, "Event tidak valid.")
                    return redirect("ticket_category_manage")

                if action == "create":
                    cursor.execute("SELECT COALESCE(SUM(quota), 0) AS total FROM ticket_category WHERE event_id = %s", [event_id])
                else:
                    cursor.execute(
                        """
                        SELECT COALESCE(SUM(quota), 0) AS total
                        FROM ticket_category
                        WHERE event_id = %s AND category_id <> %s
                        """,
                        [event_id, category_id],
                    )
                total_quota = fetchone(cursor)["total"]

                if total_quota + quota > event["capacity"]:
                    messages.error(request, f"Gagal! Total kuota melebihi kapasitas venue ({event['capacity']} kursi).")
                    return redirect("ticket_category_manage")

                if action == "create":
                    cursor.execute(
                        """
                        INSERT INTO ticket_category (category_id, category_name, quota, price, event_id)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        [str(uuid.uuid4()), category_name, quota, price, event_id],
                    )
                    messages.success(request, "Kategori Tiket baru berhasil dibuat!")
                elif action == "update":
                    cursor.execute(
                        """
                        UPDATE ticket_category
                        SET category_name = %s, quota = %s, price = %s, event_id = %s
                        WHERE category_id = %s
                        """,
                        [category_name, quota, price, event_id, category_id],
                    )
                    messages.success(request, "Data Kategori Tiket berhasil diperbarui!")
        except (ValueError, TypeError):
            messages.error(request, "Format Kuota atau Harga tidak valid!")
        except DatabaseError as exc:
            messages.error(request, f"Terjadi kesalahan: {exc}")

        return redirect("ticket_category_manage")

    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT tc.category_id, tc.category_name, tc.quota, tc.price,
                   e.event_id, e.event_title
            FROM ticket_category tc
            JOIN event e ON e.event_id = tc.event_id
            ORDER BY e.event_title, tc.category_name
            """
        )
        categories = [
            {
                "category_id": row["category_id"],
                "category_name": row["category_name"],
                "quota": row["quota"],
                "price": row["price"],
                "event": {"event_id": row["event_id"], "event_title": row["event_title"]},
            }
            for row in fetchall(cursor)
        ]

        cursor.execute(
            """
            SELECT e.event_id, e.event_title, v.capacity
            FROM event e
            JOIN venue v ON v.venue_id = e.venue_id
            ORDER BY e.event_title
            """
        )
        events = [{"event_id": row["event_id"], "event_title": row["event_title"], "venue": {"capacity": row["capacity"]}} for row in fetchall(cursor)]

    return render(request, "ticket_category_manage.html", {"categories": categories, "events": events, "role": role})




def seats_view(request):
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT s.seat_id, s.section, s.row_number, s.seat_number, v.venue_name
            FROM seat s
            JOIN venue v ON v.venue_id = s.venue_id
            ORDER BY v.venue_name, s.section, s.row_number, s.seat_number
            """
        )
        seats = [
            {
                "seat_id": row["seat_id"],
                "section": row["section"],
                "row_number": row["row_number"],
                "seat_number": row["seat_number"],
                "venue": {"venue_name": row["venue_name"]},
            }
            for row in fetchall(cursor)
        ]
    return render(request, "seats.html", {"seats": seats})

def list_event(request):
    role = request.session.get('role', 'GUEST')
    user_id = request.session.get('user_id', '0')

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action')
            event_id = data.get('event_id')

            with transaction.atomic(): 
                with db_cursor() as cursor:
                    if action == 'DELETE':
                        # Hapus relasi anak terlebih dahulu agar tidak melanggar foreign key constraint
                        cursor.execute("DELETE FROM event_artist WHERE event_id = %s", [event_id])
                        cursor.execute("DELETE FROM ticket_category WHERE event_id = %s", [event_id])
                        cursor.execute("DELETE FROM event WHERE event_id = %s", [event_id])
                        
                        return JsonResponse({'status': 'success'})
                        
                    if action in ['CREATE', 'UPDATE']:
                        # Cari venue_id berdasarkan nama venue yang dikirim modal
                        cursor.execute("SELECT venue_id FROM venue WHERE venue_name = %s LIMIT 1", [data.get('venue')])
                        venue_row = fetchone(cursor)
                        if not venue_row:
                            return JsonResponse({'status': 'error', 'message': 'Venue tidak ditemukan'}, status=404)
                        venue_id_target = venue_row['venue_id']
                        
                        # Jika role adalah ORGANIZER, gunakan user_id miliknya langsung sebagai organizer_id
                        if role == 'ORGANIZER':
                            # Ambil organizer_id dari tabel organizer berdasarkan user_id yang sedang login
                            cursor.execute("SELECT organizer_id FROM organizer WHERE user_id = %s LIMIT 1", [user_id])
                            org_row = fetchone(cursor)
                            if not org_row:
                                return JsonResponse({'status': 'error', 'message': 'Profil Organizer tidak ditemukan.'}, status=404)
                            organizer_id_target = org_row['organizer_id']
                        elif role == 'ADMIN':
                            # Jika ADMIN yang membuat, ambil organizer_id yang dikirim dari form frontend
                            # Jika frontend tidak mengirimkannya, baru gunakan fallback ambil data pertama
                            organizer_id_target = data.get('organizer_id')
                            if not organizer_id_target:
                                cursor.execute("SELECT organizer_id FROM organizer LIMIT 1")
                                org_row = fetchone(cursor)
                                organizer_id_target = org_row['organizer_id'] if org_row else None
                        else:
                            return JsonResponse({'status': 'error', 'message': 'Akses ditolak'}, status=403)
                        
                        final_event_id = event_id if action == 'UPDATE' else str(uuid.uuid4())
                        event_datetime = f"{data.get('date')} {data.get('time')}"

                        # Tiru gaya update_or_create dengan PostgreSQL UPSERT (ON CONFLICT)
                        cursor.execute(
                            """
                            INSERT INTO event (event_id, event_title, event_datetime, venue_id, organizer_id)
                            VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (event_id) 
                            DO UPDATE SET 
                                event_title = EXCLUDED.event_title,
                                event_datetime = EXCLUDED.event_datetime,
                                venue_id = EXCLUDED.venue_id,
                                organizer_id = EXCLUDED.organizer_id
                            """,
                            [final_event_id, data.get('name'), event_datetime, venue_id_target, organizer_id_target]
                        )

                        # Hapus & simpan ulang relasi artist
                        cursor.execute("DELETE FROM event_artist WHERE event_id = %s", [final_event_id])
                        for artist_id in data.get('artists', []):
                            cursor.execute(
                                "INSERT INTO event_artist (event_id, artist_id, role) VALUES (%s, %s, 'MAIN')",
                                [final_event_id, artist_id]
                            )
                            
                        # Hapus & simpan ulang Kategori Tiket 
                        cursor.execute("DELETE FROM ticket_category WHERE event_id = %s", [final_event_id])
                        for cat in data.get('categories', []):
                            cursor.execute(
                                """
                                INSERT INTO ticket_category (category_id, category_name, price, quota, event_id)
                                VALUES (%s, %s, %s, %s, %s)
                                """,
                                [str(uuid.uuid4()), cat['name'], Decimal(cat['price']), int(cat['stock']), final_event_id]
                            )

            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    # --- PROSES GET DATA (FILTER DAN SEARCHING) ---
    search_query = request.GET.get('q', '')
    venue_filter = request.GET.get('venue', '')
    artist_filter = request.GET.get('artist', '')

    # Struktur query dasar
    base_query = """
        SELECT e.event_id, e.event_title, e.event_datetime, e.organizer_id, v.venue_name, v.venue_id
        FROM event e
        JOIN venue v ON v.venue_id = e.venue_id
    """
    conditions = []
    params = []

    if search_query:
        conditions.append("e.event_title ILIKE %s")
        params.append(f"%{search_query}%")
    if venue_filter:
        conditions.append("e.venue_id = %s")
        params.append(venue_filter)
    if artist_filter:
        conditions.append("""
            e.event_id IN (
                SELECT event_id FROM event_artist WHERE artist_id = %s
            )
        """)
        params.append(artist_filter)

    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)

    with db_cursor() as cursor:
        cursor.execute(base_query, params)
        raw_events = fetchall(cursor)

        events_data = []
        for row in raw_events:
            eid = row['event_id']

            # Ambil daftar kategori tiket dan harga minimal untuk event ini
            cursor.execute(
                """
                SELECT category_name, price, quota 
                FROM ticket_category 
                WHERE event_id = %s
                """, [eid]
            )
            cats = fetchall(cursor)
            
            cursor.execute("SELECT MIN(price) AS min_price FROM ticket_category WHERE event_id = %s", [eid])
            min_p_row = fetchone(cursor)
            min_p = min_p_row['min_price'] if min_p_row and min_p_row['min_price'] else 0

            # Ambil nama-nama artis yang berelasi dengan event ini
            cursor.execute(
                """
                SELECT a.name 
                FROM event_artist ea
                JOIN artist a ON ea.artist_id = a.artist_id
                WHERE ea.event_id = %s
                """, [eid]
            )
            artists_list = [a['name'] for a in fetchall(cursor)]

            # Bangun struktur data penampung agar sesuai dengan kebutuhan template JavaScript Anda
            events_data.append({
                'id': eid,
                'name': row['event_title'],
                'date': row['event_datetime'].strftime('%Y-%m-%d') if row['event_datetime'] else '',
                'time': row['event_datetime'].strftime('%H:%M') if row['event_datetime'] else '',
                'venue': row['venue_name'],
                'organizer_id': str(row['organizer_id']) if row['organizer_id'] else '',
                'artists': artists_list,
                'categories': [{'name': c['category_name'], 'price': int(c['price']), 'stock': c['quota']} for c in cats],
                'min_price': int(min_p)
            })

        # Mengambil opsi data dropdown untuk filter di halaman depan
        cursor.execute("SELECT venue_id, venue_name FROM venue ORDER BY venue_name")
        all_venues = fetchall(cursor)

        cursor.execute("SELECT artist_id, name FROM artist ORDER BY name")
        all_artists = fetchall(cursor)

    # Default ID yang dikirim ke JS adalah user_id dari session
    js_user_id = user_id 
    
    # Jika role-nya adalah ORGANIZER, kita konversi id-nya menjadi organizer_id
    if role == 'ORGANIZER':
        with db_cursor() as cursor:
            cursor.execute("SELECT organizer_id FROM organizer WHERE user_id = %s LIMIT 1", [user_id])
            org_row = fetchone(cursor)
            if org_row:
                js_user_id = org_row['organizer_id']

    context = {
        'role': role,
        'current_user_id': js_user_id,
        'events_js': json.dumps(events_data, default=str), 
        'venues': all_venues,
        'artists': all_artists,
    }
    return render(request, 'event.html', context)

def list_venue(request):
    role = request.session.get('role', 'GUEST')
    user_id = request.session.get('user_id')

    with db_cursor() as cursor:
        # 1. Ambil semua data venue
        cursor.execute("""
            SELECT venue_id, venue_name, address, city, capacity, has_reserved_seating, organizer_id 
            FROM venue 
            ORDER BY venue_name
        """)
        venues_qs = fetchall(cursor)

        # 2. Ambil data statistik/agregasi dalam satu query
        cursor.execute("""
            SELECT 
                COUNT(*) AS total_venue,
                COALESCE(SUM(capacity), 0) AS total_capacity,
                COUNT(CASE WHEN has_reserved_seating = TRUE THEN 1 END) AS total_reserved
            FROM venue
        """)
        stats = fetchone(cursor)

    # === PENYEMPURNAAN LOGIKA DI SINI ===
    current_organizer_id = None
    if role == 'ORGANIZER' and user_id:
        with db_cursor() as cursor:
            cursor.execute("SELECT organizer_id FROM organizer WHERE user_id = %s LIMIT 1", [user_id])
            org_row = fetchone(cursor)
            if org_row and org_row['organizer_id']:
                # Kita paksa konversi ke string huruf kecil agar aman dibanding di HTML
                current_organizer_id = str(org_row['organizer_id']).lower()

    # Kita bersihkan data venues_qs agar semua organizer_id berupa string murni / string kosong
    cleaned_venues = []
    for venue in venues_qs:
        # Konversi data asli dari DB agar tidak error saat dibaca oleh template
        v_org_id = str(venue['organizer_id']).lower() if venue.get('organizer_id') else ''
        
        # Tentukan langsung di backend apakah user ini punya hak akses edit/hapus
        can_manage = False
        if role == 'ADMIN':
            can_manage = True
        elif role == 'ORGANIZER' and current_organizer_id and v_org_id == current_organizer_id:
            can_manage = True

        cleaned_venues.append({
            'venue_id': venue['venue_id'],
            'venue_name': venue['venue_name'],
            'address': venue['address'],
            'city': venue['city'],
            'capacity': venue['capacity'],
            'has_reserved_seating': venue['has_reserved_seating'],
            'organizer_id': v_org_id,
            'can_manage': can_manage # <--- Kita buatkan bendera (flag) instan untuk HTML
        })

    context = {
        'venues': cleaned_venues, # Menggunakan data yang sudah dibersihkan
        'role': role,
        'stats': {
            'total_venue': stats['total_venue'] if stats else 0,
            'total_reserved': stats['total_reserved'] if stats else 0,
            'total_capacity': stats['total_capacity'] if stats else 0,
        }
    }

    return render(request, 'venue.html', context)

def venue_manage_view(request):
    if request.method == 'POST':
        try:
            role = request.session.get('role', 'GUEST')
            user_id = request.session.get('user_id')
            
            action = request.POST.get('action')
            venue_id = request.POST.get('venue_id')
            nama = request.POST.get('nama')
            alamat = request.POST.get('alamat')
            kota = request.POST.get('kota')
            kapasitas = request.POST.get('kapasitas')
            reserved = request.POST.get('reserved') == 'on'

            # Validasi input data wajib
            if action in ['CREATE', 'UPDATE']:
                if not nama or not alamat or not kota or not kapasitas:
                    return JsonResponse({'status': 'error', 'message': 'Semua field wajib diisi!'}, status=400)
                if int(kapasitas) <= 0:
                    return JsonResponse({'status': 'error', 'message': 'Kapasitas harus lebih dari 0!'}, status=400)

            # Ambil detail organizer_id pengakses jika role-nya ORGANIZER
            user_organizer_id = None
            if role == 'ORGANIZER':
                with db_cursor() as cursor:
                    cursor.execute("SELECT organizer_id FROM organizer WHERE user_id = %s LIMIT 1", [user_id])
                    org_row = fetchone(cursor)
                    user_organizer_id = org_row['organizer_id'] if org_row else None

            with transaction.atomic():
                with db_cursor() as cursor:
                    
                    if action == 'CREATE':
                        # Validasi Role Akses Pembuatan
                        if role not in ['ADMIN', 'ORGANIZER']:
                            return JsonResponse({'status': 'error', 'message': 'Anda tidak memiliki hak akses ini.'}, status=403)
                        
                        # Simpan data baru beserta ID Organizernya (Jika Admin, nilainya NULL/None)
                        cursor.execute(
                            """
                            INSERT INTO venue (venue_id, venue_name, address, city, capacity, has_reserved_seating, organizer_id)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """,
                            [str(uuid.uuid4()), nama, alamat, kota, int(kapasitas), reserved, user_organizer_id]
                        )

                    elif action == 'UPDATE':
                        # PROTEKSI BACKEND: Cek kepemilikan data sebelum update
                        if role == 'ORGANIZER':
                            cursor.execute("SELECT organizer_id FROM venue WHERE venue_id = %s", [venue_id])
                            v_row = fetchone(cursor)
                            if not v_row or str(v_row['organizer_id']) != str(user_organizer_id):
                                return JsonResponse({'status': 'error', 'message': 'Akses ditolak! Anda bukan pemilik venue ini.'}, status=403)
                        elif role != 'ADMIN':
                            return JsonResponse({'status': 'error', 'message': 'Akses ditolak!'}, status=403)

                        cursor.execute(
                            """
                            UPDATE venue 
                            SET venue_name = %s, address = %s, city = %s, capacity = %s, has_reserved_seating = %s
                            WHERE venue_id = %s
                            """,
                            [nama, alamat, kota, int(kapasitas), reserved, venue_id]
                        )

                    elif action == 'DELETE':
                        # PROTEKSI BACKEND: Cek kepemilikan data sebelum hapus
                        if role == 'ORGANIZER':
                            cursor.execute("SELECT organizer_id FROM venue WHERE venue_id = %s", [venue_id])
                            v_row = fetchone(cursor)
                            if not v_row or str(v_row['organizer_id']) != str(user_organizer_id):
                                return JsonResponse({'status': 'error', 'message': 'Akses ditolak! Anda bukan pemilik venue ini.'}, status=403)
                        elif role != 'ADMIN':
                            return JsonResponse({'status': 'error', 'message': 'Akses ditolak!'}, status=403)

                        # Cek apakah venue sedang digunakan oleh event apa pun
                        cursor.execute("SELECT 1 FROM event WHERE venue_id = %s LIMIT 1", [venue_id])
                        if cursor.fetchone():
                            return JsonResponse({
                                'status': 'error', 
                                'message': 'Gagal menghapus! Venue ini sedang digunakan oleh sebuah event.'
                            }, status=400)

                        cursor.execute("DELETE FROM venue WHERE venue_id = %s", [venue_id])
                    
                    else:
                        return JsonResponse({'status': 'error', 'message': 'Action tidak valid'}, status=400)
            
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
            
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)
        
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
        
        with connection.cursor() as cursor:
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

    with connection.cursor() as cursor:
        if request.method == "GET":
            ticket_filter = (request.GET.get('ticket_filter') or '').strip()
            status_filter = (request.GET.get('ticket_status') or '').strip()

            ##TODO: perlu sort keknya
            base_query = """
                select * from ticket t 
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
                conditions.append("c.customer_id = %s")
                params.append(user_id)
            elif role == 'ORGANIZER':
                conditions.append("e.organizer_id = %s")
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

            # TODO: Paid atau gmn
            # cursor.execute("select distinct payment_status from orders")
            # statuses = cursor.fetchall()
            statuses = ["PAID", "PENDING", "REJECTED"]

            orders_options = []
            events_options = []
            categories_options = []
            seats_options = []
            
            if role in ('ADMIN', 'ORGANIZER'):
                cursor.execute("select * from orders o join customer c on c.customer_id = o.customer_id")
                orders_options = dictfetchall(cursor)
                
                events_options_query = f"select * from event{
                    f" where organizer_id = {user_id}" if role == 'ORGANIZER' else ""}"

                cursor.execute(events_options_query)
                events_options = dictfetchall(cursor)
                
                categories_options_query = f"""
                    select 
                        tc.category_id, 
                        tc.category_name, 
                        e.event_title, 
                        tc.event_id, 
                        tc.price as harga, 
                        tc.quota, 
                        coalesce(count(t.ticket_id), 0) as terpakai
                    from ticket_category tc 
                    join {
                        f"(select * from event where organizer_id = {user_id})" 
                        if role == 'ORGANIZER' else "event"
                    } e on tc.event_id = e.event_id
                    left join ticket t on tc.category_id = t.tcategory_id
                    group by tc.category_id, tc.category_name, e.event_title, tc.event_id, tc.price, tc.quota
                    having coalesce(count(t.ticket_id), 0) < tc.quota
                """
                cursor.execute(categories_options_query)
                categories_options = dictfetchall(cursor)
                
                seats_options_query = f"""
                    select *,
                        (select hr.ticket_id
                         from has_relationship hr
                         join ticket t on hr.ticket_id = t.ticket_id
                         join ticket_category tc on t.tcategory_id = tc.category_id
                         where hr.seat_id = s.seat_id and tc.event_id = e.event_id
                         limit 1) as occupied_by_ticket_id
                    from seat s 
                    join event e on s.venue_id = e.venue_id
                    {f" where e.organizer_id = {user_id}" if role == 'ORGANIZER' else ""}
                """
                cursor.execute(seats_options_query)
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
    
