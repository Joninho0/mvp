"""Views for customers app."""

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET", "POST"])
def login_view(request):
    """Handle user login."""
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        user = authenticate(request, email=email, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get("next", "dashboard")
            return redirect(next_url)
        else:
            return render(
                request,
                "registration/login.html",
                {"form": {"errors": True}},
                status=400,
            )
    return render(request, "registration/login.html")


@require_http_methods(["GET", "POST"])
def register_view(request):
    """Handle user registration."""
    from apps.customers.forms import UserRegistrationForm

    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("dashboard")
    else:
        form = UserRegistrationForm()
    return render(request, "registration/register.html", {"form": form})


@login_required
@require_http_methods(["POST"])
def logout_view(request):
    """Handle user logout."""
    logout(request)
    return redirect("login")