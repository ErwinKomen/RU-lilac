from django.shortcuts import render, redirect

def view_404(request, exception):
    return redirect('home')