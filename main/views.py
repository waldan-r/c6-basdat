from django.shortcuts import render
import uuid

# Create your views here.
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import UserAccount, AccountRole, Customer, Organizer, Role, Artist, TicketCategory, Event

def login_view(request):
    # login
    if request.method == 'POST':
        username_input = request.POST.get('email')
        password_input = request.POST.get('password')

        try:
            # validate
            user = UserAccount.objects.get(username=username_input, password=password_input)
            
            # retrieve role
            account_role = AccountRole.objects.filter(user=user).first()
            role_name = account_role.role.role_name if account_role else 'GUEST'

            # save session
            request.session['user_id'] = user.user_id
            request.session['username'] = user.username
            request.session['role'] = role_name
            
            return redirect('dashboard')
            
        except UserAccount.DoesNotExist:
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
        
        # validasi Dasar
        if password != confirm_password:
            messages.error(request, "Konfirmasi password tidak cocok!")
            return redirect('register')
        
        if len(password) < 6:
            messages.error(request, "Password minimal 6 karakter!")
            return redirect('register')

        if UserAccount.objects.filter(username=username).exists():
            messages.error(request, "Username sudah terdaftar!")
            return redirect('register')

        try:
            # buat user_account
            user_id = str(uuid.uuid4())
            user = UserAccount.objects.create(
                user_id=user_id,
                username=username,
                password=password
            )

            # tentukan Role ID berdasarkan pilihan
            role_map = {
                'admin': '38aaec88-4c72-435d-b1a6-f761d6f0075c',
                'customer': 'a5352506-2c32-4126-aa16-26b82baec8eb',
                'organizer': '7d4dbc8d-c9c3-49d9-9403-b463a456ef50'
            }
            
            selected_role_id = role_map.get(role_choice)
            role_obj = Role.objects.get(role_id=selected_role_id)
            
            # simpan ke AccountRole
            AccountRole.objects.create(role=role_obj, user=user)

            # simpan ke tabel customer/organizer
            if role_choice == 'customer':
                Customer.objects.create(
                    customer_id=str(uuid.uuid4()),
                    full_name=request.POST.get('full_name'),
                    phone_number=request.POST.get('phone_number'),
                    user=user
                )
            elif role_choice == 'organizer':
                Organizer.objects.create(
                    organizer_id=str(uuid.uuid4()),
                    organizer_name=request.POST.get('full_name'),
                    contact_email=request.POST.get('email'),
                    user=user
                )

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
    # akses untuk semua orang
    artists = Artist.objects.all()
    context = {
        'artists': artists,
        'role': request.session.get('role', 'GUEST')
    }
    return render(request, 'artists.html', context)

def artist_manage_view(request):

    if request.method == 'POST':
        action = request.POST.get('action')

        # CREATE ARTIST
        if action == 'create':
            name = request.POST.get('name')
            genre = request.POST.get('genre', '')
            
            if not name:
                messages.error(request, "Name wajib diisi!")
            else:
                Artist.objects.create(
                    artist_id=str(uuid.uuid4()),
                    name=name,
                    genre=genre
                )
                messages.success(request, "Artist baru berhasil ditambahkan!")

        # UPDATE ARTIST
        elif action == 'update':
            artist_id = request.POST.get('artist_id')
            name = request.POST.get('name')
            genre = request.POST.get('genre', '')

            if not name:
                messages.error(request, "Name wajib diisi!")
            else:
                try:
                    artist = Artist.objects.get(artist_id=artist_id)
                    artist.name = name
                    artist.genre = genre
                    artist.save()
                    messages.success(request, "Data artist berhasil diperbarui!")
                except Artist.DoesNotExist:
                    messages.error(request, "Data artist tidak ditemukan!")

        # DELETE ARTIST
        elif action == 'delete':
            artist_id = request.POST.get('artist_id')
            try:
                artist = Artist.objects.get(artist_id=artist_id)
                artist.delete()
                messages.success(request, "Artist berhasil dihapus!")
            except Artist.DoesNotExist:
                messages.error(request, "Data artist tidak ditemukan!")

        return redirect('artist_manage')

    artists = Artist.objects.all()
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

        # delete ticket category
        if action == 'delete':
            category_id = request.POST.get('category_id')
            try:
                category = TicketCategory.objects.get(category_id=category_id)
                category.delete()
                messages.success(request, f"Kategori Tiket '{category.category_name}' berhasil dihapus!")
            except TicketCategory.DoesNotExist:
                messages.error(request, "Data kategori tiket tidak ditemukan!")
            return redirect('ticket_category_manage')

        # ambil input untuk create update
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
        try:
            event = Event.objects.select_related('venue').get(event_id=event_id)
            venue_capacity = event.venue.capacity
        except Event.DoesNotExist:
            messages.error(request, "Event tidak valid.")
            return redirect('ticket_category_manage')

        if action == 'create':
            # hitung total kuota saat ini untuk event tersebut
            current_total_quota = TicketCategory.objects.filter(event=event).aggregate(total=Sum('quota'))['total'] or 0
            
            if current_total_quota + quota > venue_capacity:
                messages.error(request, f"Gagal! Total kuota melebihi kapasitas venue ({venue_capacity} kursi).")
            else:
                TicketCategory.objects.create(
                    category_id=str(uuid.uuid4()),
                    category_name=category_name,
                    quota=quota,
                    price=price,
                    event=event
                )
                messages.success(request, "Kategori Tiket baru berhasil dibuat!")

        # update ticket category
        elif action == 'update':
            category_id = request.POST.get('category_id')
            try:
                category = TicketCategory.objects.get(category_id=category_id)
                
                other_categories_quota = TicketCategory.objects.filter(event=event).exclude(category_id=category_id).aggregate(total=Sum('quota'))['total'] or 0
                
                if other_categories_quota + quota > venue_capacity:
                    messages.error(request, f"Gagal Update! Total kuota melebihi kapasitas venue ({venue_capacity} kursi).")
                else:
                    category.category_name = category_name
                    category.quota = quota
                    category.price = price
                    category.save()
                    messages.success(request, "Data Kategori Tiket berhasil diperbarui!")
            except TicketCategory.DoesNotExist:
                messages.error(request, "Kategori tiket tidak ditemukan!")

        return redirect('ticket_category_manage')

    # semua roles allowed melakukan Get
    categories = TicketCategory.objects.select_related('event').order_by('event__event_title', 'category_name')
    events = Event.objects.all()
    
    # role sudah dilempar ke context di bawah, sehingga bisa dipakai di HTML
    context = {
        'categories': categories,
        'events': events,
        'role': role 
    }
    return render(request, 'ticket_category_manage.html', context)

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

