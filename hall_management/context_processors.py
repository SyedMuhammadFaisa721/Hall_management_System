from django.utils import timezone


def greeting_context(request):
    hour = timezone.localtime().hour
    if 5 <= hour < 12:
        greeting = "GOOD MORNING"
    elif 12 <= hour < 18:
        greeting = "GOOD AFTERNOON"
    elif 18 <= hour < 21:
        greeting = "GOOD EVENING"
    else:
        greeting = "GOOD NIGHT"

    return {"greeting": greeting}