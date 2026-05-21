import json
import uuid
from decimal import Decimal

from django.contrib import messages
from django.db import DatabaseError, connection, transaction
from django.shortcuts import redirect, render


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
    with db_cursor() as cursor:
        cursor.execute("SELECT artist_id, name, genre FROM artist ORDER BY name")
        artists = fetchall(cursor)
    return render(request, "artists.html", {"artists": artists, "role": request.session.get("role", "GUEST")})


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


def list_event(request):
    role = request.session.get("role", "ADMIN")

    with db_cursor() as cursor:
        cursor.execute("SELECT venue_id AS id, venue_name AS name, city FROM venue ORDER BY venue_name")
        venues = fetchall(cursor)

        cursor.execute("SELECT artist_id AS id, name FROM artist ORDER BY name")
        artists = fetchall(cursor)

        cursor.execute(
            """
            SELECT e.event_id AS id, e.event_title AS name,
                   e.event_datetime::date AS date,
                   to_char(e.event_datetime, 'HH24:MI') AS time,
                   v.venue_name AS venue,
                   COALESCE(MIN(tc.price), 0) AS min_price,
                   COALESCE(string_agg(DISTINCT a.name, ', '), '') AS artists
            FROM event e
            JOIN venue v ON v.venue_id = e.venue_id
            LEFT JOIN ticket_category tc ON tc.event_id = e.event_id
            LEFT JOIN event_artist ea ON ea.event_id = e.event_id
            LEFT JOIN artist a ON a.artist_id = ea.artist_id
            GROUP BY e.event_id, e.event_title, e.event_datetime, v.venue_name
            ORDER BY e.event_datetime
            """
        )
        events = fetchall(cursor)

        cursor.execute(
            """
            SELECT event_id, category_name AS name, price, quota AS stock
            FROM ticket_category
            ORDER BY category_name
            """
        )
        category_rows = fetchall(cursor)

    for event in events:
        event["date"] = event["date"].isoformat()
        event["id"] = str(event["id"])
        event["min_price"] = float(event["min_price"])
        event["categories"] = [
            {"name": c["name"], "price": float(c["price"]), "stock": c["stock"]}
            for c in category_rows
            if str(c["event_id"]) == event["id"]
        ] or [{"name": "Tiket", "price": float(event["min_price"]), "stock": 0}]
        event["artists_list"] = [name.strip() for name in event["artists"].split(",") if name.strip()]

    return render(
        request,
        "event.html",
        {"role": role, "events": events, "events_json": json.dumps(events, default=str), "venues": venues, "artists": artists},
    )


def list_venue(request):
    role = request.session.get("role", "GUEST")
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT v.venue_id, v.venue_name, v.address, v.city, v.capacity,
                   EXISTS (SELECT 1 FROM seat s WHERE s.venue_id = v.venue_id) AS has_reserved
            FROM venue v
            ORDER BY v.venue_name
            """
        )
        venues = fetchall(cursor)
    return render(request, "venue.html", {"venues": venues, "role": role})


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


def ticket_view(request):
    role = request.session.get("role", "GUEST")
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT t.ticket_id, t.ticket_code,
                   tc.category_id, tc.category_name,
                   e.event_id, e.event_title,
                   o.order_id, o.total_amount, o.payment_status,
                   c.customer_id, c.full_name
            FROM ticket t
            JOIN ticket_category tc ON tc.category_id = t.tcategory_id
            JOIN event e ON e.event_id = tc.event_id
            JOIN orders o ON o.order_id = t.torder_id
            JOIN customer c ON c.customer_id = o.customer_id
            ORDER BY e.event_datetime, t.ticket_code
            """
        )
        rows = fetchall(cursor)

    tickets = [
        {
            "ticket_id": row["ticket_id"],
            "ticket_code": row["ticket_code"],
            "tcategory": {
                "category_id": row["category_id"],
                "category_name": row["category_name"],
                "event": {"event_id": row["event_id"], "event_title": row["event_title"]},
            },
            "torder": {
                "order_id": row["order_id"],
                "total_amount": row["total_amount"],
                "payment_status": row["payment_status"],
                "customer": {"customer_id": row["customer_id"], "full_name": row["full_name"]},
            },
        }
        for row in rows
    ]

    template = "my_tickets.html" if role == "CUSTOMER" else "ticket_manage.html"
    return render(request, template, {"tickets": tickets})


def placeholder(request, *args, **kwargs):
    return list_venue(request)
