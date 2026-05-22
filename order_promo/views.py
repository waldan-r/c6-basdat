from decimal import Decimal
from uuid import UUID

from django.db import connection, transaction
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone


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


def is_uuid(value):
    try:
        UUID(str(value))
    except (TypeError, ValueError):
        return False
    return True


def rupiah(value):
    return f"{Decimal(value or 0):,.0f}".replace(",", ".")


def get_customer_id(request):
    customer_id = request.POST.get("customer_id") or request.GET.get("customer_id")
    if is_uuid(customer_id):
        return customer_id

    with db_cursor() as cursor:
        cursor.execute("SELECT customer_id FROM customer ORDER BY full_name LIMIT 1")
        row = cursor.fetchone()
    return row[0] if row else None


def event_list(request):
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT e.event_id, e.event_title, e.event_datetime, v.venue_name, v.city
            FROM event e
            JOIN venue v ON v.venue_id = e.venue_id
            ORDER BY e.event_datetime
            """
        )
        events = fetchall(cursor)

    return render(request, "order_promo/event_list.html", {"events": events, "title": "Cari Event"})


def checkout(request):
    event_id = request.POST.get("event_id") or request.GET.get("event_id")
    if not is_uuid(event_id):
        return redirect("order_promo:event_list")

    customer_id = get_customer_id(request)
    error = None

    if request.method == "POST":
        category_id = request.POST.get("category_id")
        promo_code = request.POST.get("promo_code", "").strip().upper()

        if not is_uuid(category_id):
            error = "Pilih kategori tiket."
        elif not customer_id:
            error = "Customer belum tersedia."
        else:
            try:
                create_order(event_id, category_id, customer_id, promo_code)
                return redirect(f"{reverse('order_promo:order_list')}?msg=created")
            except ValueError as exc:
                error = str(exc)

    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT e.event_id, e.event_title, e.event_datetime, v.venue_name, v.city
            FROM event e
            JOIN venue v ON v.venue_id = e.venue_id
            WHERE e.event_id = %s
            """,
            [event_id],
        )
        event = fetchone(cursor)

        cursor.execute(
            """
            SELECT category_id, category_name, quota, price
            FROM ticket_category
            WHERE event_id = %s
            ORDER BY price
            """,
            [event_id],
        )
        categories = fetchall(cursor)

    if event is None:
        return redirect("order_promo:event_list")

    for category in categories:
        category["price_display"] = rupiah(category["price"])

    return render(
        request,
        "order_promo/checkout.html",
        {
            "event": event,
            "categories": categories,
            "customer_id": customer_id,
            "error": error,
            "title": "Checkout",
        },
    )


def create_order(event_id, category_id, customer_id, promo_code):
    with transaction.atomic():
        with db_cursor() as cursor:
            cursor.execute(
                "SELECT price FROM ticket_category WHERE category_id = %s AND event_id = %s",
                [category_id, event_id],
            )
            category = fetchone(cursor)
            if category is None:
                raise ValueError("Kategori tiket tidak valid.")

            total_amount = category["price"]
            promotion_id = None

            if promo_code:
                cursor.execute(
                    """
                    SELECT p.promotion_id, p.discount_type, p.discount_value, p.usage_limit,
                           COUNT(op.order_promotion_id) AS used_count
                    FROM promotion p
                    LEFT JOIN order_promotion op ON op.promotion_id = p.promotion_id
                    WHERE p.promo_code = %s
                      AND CURRENT_DATE BETWEEN p.start_date AND p.end_date
                    GROUP BY p.promotion_id, p.discount_type, p.discount_value, p.usage_limit
                    """,
                    [promo_code],
                )
                promotion = fetchone(cursor)
                if promotion is None:
                    raise ValueError("Kode promo tidak valid.")
                if promotion["used_count"] >= promotion["usage_limit"]:
                    raise ValueError("Batas penggunaan promo sudah habis.")

                promotion_id = promotion["promotion_id"]
                if promotion["discount_type"] == "PERCENTAGE":
                    total_amount -= total_amount * promotion["discount_value"] / Decimal("100")
                else:
                    total_amount -= promotion["discount_value"]
                total_amount = max(total_amount, Decimal("0"))

            cursor.execute(
                """
                INSERT INTO orders (order_id, order_date, payment_status, total_amount, customer_id)
                VALUES (gen_random_uuid(), %s, 'PENDING', %s, %s)
                RETURNING order_id
                """,
                [timezone.now(), total_amount, customer_id],
            )
            order_id = cursor.fetchone()[0]

            if promotion_id:
                cursor.execute(
                    """
                    INSERT INTO order_promotion (order_promotion_id, promotion_id, order_id)
                    VALUES (gen_random_uuid(), %s, %s)
                    """,
                    [promotion_id, order_id],
                )

            cursor.execute(
                """
                INSERT INTO ticket (ticket_id, ticket_code, tcategory_id, torder_id)
                VALUES (gen_random_uuid(), 'TCK-' || floor(random() * 1000000)::text, %s, %s)
                """,
                [category_id, order_id],
            )


def order_list(request):
    role = request.GET.get("role", "customer").upper()

    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT o.order_id, o.order_date, o.payment_status, o.total_amount,
                   c.full_name AS customer_name,
                   COALESCE(string_agg(DISTINCT p.promo_code, ', '), '-') AS promo_codes
            FROM orders o
            JOIN customer c ON c.customer_id = o.customer_id
            LEFT JOIN order_promotion op ON op.order_id = o.order_id
            LEFT JOIN promotion p ON p.promotion_id = op.promotion_id
            GROUP BY o.order_id, o.order_date, o.payment_status, o.total_amount, c.full_name
            ORDER BY o.order_date DESC
            """
        )
        orders = fetchall(cursor)

    for order in orders:
        order["total_display"] = rupiah(order["total_amount"])

    return render(
        request,
        "order_promo/order_list.html",
        {"orders": orders, "role": role, "title": "Daftar Order"},
    )


def order_update(request):
    if request.method == "POST":
        order_id = request.POST.get("order_id")
        payment_status = request.POST.get("payment_status")
        if is_uuid(order_id) and payment_status in {"PENDING", "PAID", "CANCELLED"}:
            with db_cursor() as cursor:
                cursor.execute(
                    "UPDATE orders SET payment_status = %s WHERE order_id = %s",
                    [payment_status, order_id],
                )
    return redirect(f"{reverse('order_promo:order_list')}?role=admin&msg=updated")


def order_delete(request):
    if request.method == "POST":
        order_id = request.POST.get("order_id")
        if is_uuid(order_id):
            with transaction.atomic():
                with db_cursor() as cursor:
                    cursor.execute(
                        """
                        DELETE FROM has_relationship
                        WHERE ticket_id IN (SELECT ticket_id FROM ticket WHERE torder_id = %s)
                        """,
                        [order_id],
                    )
                    cursor.execute("DELETE FROM ticket WHERE torder_id = %s", [order_id])
                    cursor.execute("DELETE FROM order_promotion WHERE order_id = %s", [order_id])
                    cursor.execute("DELETE FROM orders WHERE order_id = %s", [order_id])
    return redirect(f"{reverse('order_promo:order_list')}?role=admin&msg=deleted")


def promotion_list(request):
    return render(request, "order_promo/promotion_list.html", promotion_context(request, "Manajemen Promosi"))


def promotion_dashboard(request):
    return render(request, "order_promo/promotion_dashboard.html", promotion_context(request, "Dashboard Promosi"))


def promotion_context(request, title):
    role = request.GET.get("role", "guest").upper()

    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT p.promotion_id, p.promo_code, p.discount_type, p.discount_value,
                   p.start_date, p.end_date, p.usage_limit,
                   COUNT(op.order_promotion_id) AS used_count
            FROM promotion p
            LEFT JOIN order_promotion op ON op.promotion_id = p.promotion_id
            GROUP BY p.promotion_id, p.promo_code, p.discount_type, p.discount_value,
                     p.start_date, p.end_date, p.usage_limit
            ORDER BY p.start_date DESC, p.promo_code
            """
        )
        promotions = fetchall(cursor)

    for promotion in promotions:
        promotion["discount_display"] = (
            f"{rupiah(promotion['discount_value'])}%"
            if promotion["discount_type"] == "PERCENTAGE"
            else f"Rp {rupiah(promotion['discount_value'])}"
        )

    return {
        "promotions": promotions,
        "role": role,
        "title": title,
        "msg": request.GET.get("msg"),
        "total_promo": len(promotions),
        "total_usage": sum(p["used_count"] for p in promotions),
        "total_percentage": sum(1 for p in promotions if p["discount_type"] == "PERCENTAGE"),
    }


def promotion_create(request):
    if request.method == "POST":
        with db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO promotion (
                    promotion_id, promo_code, discount_type, discount_value,
                    start_date, end_date, usage_limit
                )
                VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s)
                """,
                [
                    request.POST.get("promo_code", "").strip().upper(),
                    request.POST.get("discount_type"),
                    request.POST.get("discount_value"),
                    request.POST.get("start_date"),
                    request.POST.get("end_date"),
                    request.POST.get("usage_limit"),
                ],
            )
    return redirect(f"{reverse('order_promo:promotion_list')}?role=admin&msg=created")


def promotion_update(request):
    if request.method == "POST":
        promotion_id = request.POST.get("promotion_id")
        if is_uuid(promotion_id):
            with db_cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE promotion
                    SET promo_code = %s,
                        discount_type = %s,
                        discount_value = %s,
                        start_date = %s,
                        end_date = %s,
                        usage_limit = %s
                    WHERE promotion_id = %s
                    """,
                    [
                        request.POST.get("promo_code", "").strip().upper(),
                        request.POST.get("discount_type"),
                        request.POST.get("discount_value"),
                        request.POST.get("start_date"),
                        request.POST.get("end_date"),
                        request.POST.get("usage_limit"),
                        promotion_id,
                    ],
                )
    return redirect(f"{reverse('order_promo:promotion_list')}?role=admin&msg=updated")


def promotion_delete(request):
    if request.method == "POST":
        promotion_id = request.POST.get("promotion_id")
        if is_uuid(promotion_id):
            with transaction.atomic():
                with db_cursor() as cursor:
                    cursor.execute("DELETE FROM order_promotion WHERE promotion_id = %s", [promotion_id])
                    cursor.execute("DELETE FROM promotion WHERE promotion_id = %s", [promotion_id])
    return redirect(f"{reverse('order_promo:promotion_list')}?role=admin&msg=deleted")
