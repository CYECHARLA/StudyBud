from django.shortcuts import redirect, render
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Q
from django.http import HttpResponse
from .models import Room, Topic, Message
from .forms import RoomForm, UserForm
from django.contrib.auth.models import User
from django.contrib import messages

# Create your views here.
# rooms = [
#     {'id':1, 'name':'Lets learn python!'},
#     {'id':2, 'name':'Design with me'},
#     {'id':3, 'name':'Frontend developers'},
# ]

def login_page(request):
    page = 'login'
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username').lower()
        password = request.POST.get('password')

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            messages.error(request, 'User does not exist')
            return redirect('login')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Incorrect password')
            return redirect('login')
    context = {'page': page}
    return render(request, 'base/login_register.html', context)

def logout_user(request):
    logout(request)
    return redirect('home')


def register_page(request):
    form = UserCreationForm()
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.username = user.username.lower()
            user.save()
            login(request, user)
            # Set session flag
            request.session['account_created'] = True
            return redirect('home')
        else:
            # This will automatically handle form error messages
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    context = {'form': form, 'error_message': messages}
    return render(request, 'base/login_register.html', context)

def home(request):
    # Get the search query for rooms and messages separately
    show_popup = request.session.pop('account_created', False)
    q = request.GET.get('q') if request.GET.get('q') else ''
    q_message = request.GET.get('q_message') if request.GET.get('q_message') else ''

    # Room search: Filter based on 'q' (for room search)
    if q:
        rooms = Room.objects.filter(
            Q(topic__name__icontains=q) |
            Q(name__icontains=q) |
            Q(description__icontains=q) |
            Q(host__username__icontains=q)
        ).distinct().order_by('-updated')
    else:
        rooms = Room.objects.all().order_by('-updated')

    # Message search: Filter based on 'q_message' (for room message search)
    if q_message:
        room_messages = Message.objects.filter(
            Q(room__topic__name__icontains=q_message) |
            Q(room__name__icontains=q_message) |
            Q(body__icontains=q_message) |
            Q(user__username__icontains=q_message)
        ).order_by('updated', '-created')
    else:
        room_messages = Message.objects.filter(Q(room__topic__name__icontains=q)).order_by('-created')[:5]

    # Topics and room count
    topics = Topic.objects.order_by('-views')[:5]
    room_count = rooms.count()

    # Context to pass to the template
    context = {
        'rooms': rooms,
        'topics': topics,
        'room_count': room_count,
        'room_messages': room_messages,
        'show_popup': show_popup,
        'popup_message': "🎉 Account created successfully!" if show_popup else "",
    }

    return render(request, 'base/home.html', context)



def room (request, pk):
    room = Room.objects.get(id=pk)
    room_messagaes = room.message_set.all().order_by('-created')
    participants = room.participants.all()
    if request.method == 'POST':
        message = Message.objects.create(
            user = request.user,
            room = room,
            body = request.POST.get('body')
        )
        room.participants.add(request.user)
        return redirect('room', pk=room.id)
    context = {'room': room, 'room_messagaes': room_messagaes, 'participants': participants}
    return render(request, 'base/room.html', context)

def user_profile(request, pk):
    user = User.objects.get(id=pk)
    rooms = user.room_set.all()
    room_messages = user.message_set.all()
    topics = Topic.objects.all()
    context = {'user': user, 'rooms': rooms, 'room_messages': room_messages, 'topics': topics}
    return render(request, 'base/profile.html', context)

@login_required(login_url='login')
def create_room(request):
    form = RoomForm()
    topics = Topic.objects.all()
    if request.method == 'POST':
        topic_name = request.POST.get('topic')
        topic , created = Topic.objects.get_or_create(name=topic_name)
        Room.objects.create(
            host = request.user,
            topic = topic,
            name = request.POST.get('name'),
            description = request.POST.get('description'),
        )
        # form = RoomForm(request.POST)
        # if form.is_valid():
        #     room = form.save(commit=False)
        #     room.host = request.user
        #     room.save()
        return redirect('home')
        
    context = {'form' : form, 'topics': topics}
    return render(request, 'base/room_form.html', context)

@login_required(login_url='login')
def update_room(request, pk):
    room = Room.objects.get(id=pk)
    form = RoomForm(instance=room)
    topics = Topic.objects.all()
    if request.user != room.host and not request.user.is_superuser:
        return HttpResponse('You are not permitted to update this room!')
    
    if request.method == 'POST':
        topic_name = request.POST.get('topic')
        topic , created = Topic.objects.get_or_create(name=topic_name)
        room.name = request.POST.get('name')
        room.topic = topic
        room.description = request.POST.get('description')
        room.save()
        # form = RoomForm(request.POST, instance=room) 
        # if form.is_valid():
        #     form.save()
        return redirect('home')
        
    context = {'form' : form, 'topics': topics, 'room': room}
    return render(request, 'base/room_form.html', context)

@login_required(login_url='login')
def delete_room(request, pk):
    room = Room.objects.get(id=pk)

    if request.user != room.host and not request.user.is_superuser:
     return HttpResponse('You are not permitted to Delete this room!')

    if request.method == 'POST':
        room.delete()
        return redirect('home')

    return render(request, 'base/delete.html', {'obj': room})

@login_required(login_url='login')
def delete_message(request, pk):
    message = Message.objects.get(id=pk)

    if request.user != message.user and not request.user.is_superuser:
        return HttpResponse('You are not permitted to delete the message!')

    if request.method == 'POST':
        room_id = message.room.id  # capture before deletion
        message.delete()

        # Check the 'next' input field from the form
        next_url = request.POST.get('next')
        if next_url and 'room' in next_url:
            return redirect('room', pk=room_id)
        elif next_url:
            return redirect(next_url)
        else:
            return redirect('home')

    return render(request, 'base/delete.html', {'obj': message})


@login_required(login_url='login')
def update_user(request):
    user = request.user
    form = UserForm(instance=user)  
    if request.method == 'POST':
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect('user-profile', pk=user.id)
    context = {'form': form}  
    return render(request, 'base/update_user.html', context)


def topics_page(request):
    q = request.GET.get('q') if request.GET.get('q') else ''
    topics = Topic.objects.filter(name__icontains=q)
    context ={'topics': topics}
    return render(request, 'base/topics_page.html', context)

def activity_page(request):
    room_messages = Message.objects.all()
    context = {'room_messages': room_messages}
    return render(request, 'base/activity.html', context)