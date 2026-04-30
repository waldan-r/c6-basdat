from django.shortcuts import render
import uuid

# Create your views here.
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import UserAccount, AccountRole, Customer, Organizer, Role, Artist

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