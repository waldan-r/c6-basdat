from django.shortcuts import render, redirect

# DATABASE DUMMY (HARDCODED)[cite: 2]
DUMMY_DB = {
    'coldplay': {
        'slug': 'coldplay',
        'title': 'Coldplay Jakarta',
        'venue': 'Stadion Utama GBK',
        'date': '2026-05-15 19:00',
        'cats': [
            {'id': 1, 'name': 'VIP', 'price': '5.000.000', 'quota': 100},
            {'id': 2, 'name': 'CAT 1', 'price': '2.500.000', 'quota': 200},
        ]
    },
    'newjeans': {
        'slug': 'newjeans',
        'title': 'NewJeans Fanmeet',
        'venue': 'ICE BSD',
        'date': '2026-06-20 18:30',
        'cats': [
            {'id': 3, 'name': 'Festival', 'price': '1.500.000', 'quota': 500},
            {'id': 4, 'name': 'VIP', 'price': '3.500.000', 'quota': 150},
        ]
    }
}

def list_event_view(request):
    """Skenario 13.a: Menampilkan daftar event"""
    return render(request, 'order/event_list.html', {'events': DUMMY_DB})

def create_order_view(request):
    """Skenario 13.a: Checkout Form (C-Order)"""
    # Ambil e=... dari URL, default ke coldplay
    event_slug = request.GET.get('e', 'coldplay')
    event = DUMMY_DB.get(event_slug, DUMMY_DB['coldplay'])
    
    success = False
    if request.method == 'POST':
        # Simulasi aksi Create Order (Langkah 5 skenario)
        success = True

    return render(request, 'order/checkout.html', {
        'event': event,
        'success': success
    })


def list_order_view(request):
    """Skenario 14: R - Order (Daftar Order berdasarkan Role)"""
    # Simulasi role dari query param: ?role=admin / organizer / customer
    user_role = request.GET.get('role', 'customer').upper()
    
    # DATABASE DUMMY ORDER
    all_orders = [
        {'id': 'ord_001', 'pelanggan': 'Budi Santoso', 'tanggal': '2024-04-10 14:32', 'status': 'LUNAS', 'total': '1.200.000'},
        {'id': 'ord_002', 'pelanggan': 'Budi Santoso', 'tanggal': '2024-04-11 09:15', 'status': 'LUNAS', 'total': '150.000'},
        {'id': 'ord_003', 'pelanggan': 'Siti Rahayu', 'tanggal': '2024-04-12 18:44', 'status': 'PENDING', 'total': '1.500.000'},
        {'id': 'ord_004', 'pelanggan': 'Siti Rahayu', 'tanggal': '2024-04-13 11:00', 'status': 'DIBATALKAN', 'total': '700.000'},
    ]

    # Statistik Dummy
    stats = {
        'total_order': len(all_orders),
        'lunas': 2,
        'pending': 0,
        'revenue': '1.350.000'
    }

    return render(request, 'order/order_list.html', {
        'role': user_role,
        'orders': all_orders,
        'stats': stats,
        'title': 'Daftar Order'
    })

def update_order_view(request):
    """Skenario 15: Update Order[cite: 2]"""
    if request.method == 'POST':
        return redirect('/order/all/?role=admin&msg=updated')
    return redirect('/order/all/?role=admin')

def order_delete_view(request):
    """Skenario 15: Delete Order[cite: 2]"""
    if request.method == 'POST':
        return redirect('/order/all/?role=admin&msg=deleted')
    return redirect('/order/all/?role=admin')

def promotion_list_view(request):
    """Skenario 16 & 17: Manajemen Promosi (Admin Only)"""
    
    promotions = [
        {'id': 1, 'code': 'PROMO10', 'type': 'Persentase (%)', 'value': 10, 'start': '2026-01-01', 'end': '2026-12-31', 'limit': 100},
        {'id': 2, 'code': 'DISKON100K', 'type': 'Nominal (Rp)', 'value': 100000, 'start': '2026-01-01', 'end': '2026-12-31', 'limit': 50},
        {'id': 3, 'code': 'GAJIAN', 'type': 'Persentase (%)', 'value': 5, 'start': '2026-01-01', 'end': '2026-12-31', 'limit': 200},
    ]
    
    msg = request.GET.get('msg')
    
    return render(request, 'order/promotion_list.html', {
        'promotions': promotions,
        'msg': msg,
        'title': 'Manajemen Promosi'
    })

def promotion_dashboard_view(request):
    """Skenario 17: Dashboard R-Promotion untuk semua role"""
    # Simulasi role: ?role=admin atau role=customer/guest/organizer
    user_role = request.GET.get('role', 'guest').upper()
    
    # Data Hardcoded sesuai Gambar 17.1
    promotions = [
        {'id': 1, 'code': 'TIKTAK20', 'type': 'PERSENTASE', 'value': '20%', 'start': '2024-01-01', 'end': '2024-12-31', 'used': 45, 'limit': 100},
        {'id': 2, 'code': 'HEMAT50K', 'type': 'NOMINAL', 'value': 'Rp 50.000', 'start': '2024-01-01', 'end': '2024-12-31', 'used': 12, 'limit': 50},
        {'id': 3, 'code': 'NEWUSER30', 'type': 'PERSENTASE', 'value': '30%', 'start': '2024-03-01', 'end': '2024-06-30', 'used': 87, 'limit': 200},
    ]
    
    stats = {
        'total_promo': 3,
        'total_usage': '144x',
        'total_percentage': 2
    }
    
    return render(request, 'order/promotion_dashboard.html', {
        'role': user_role,
        'promotions': promotions,
        'stats': stats,
        'title': 'Dashboard Promosi'
    })