from django.conf import settings
from django.db import models
from django.utils.text import slugify


def _generate_slug(name):
    from nanoid import generate
    base = slugify(name)[:40] or "tournament"
    suffix = generate(size=6)
    return f"{base}-{suffix}"


class Tournament(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        OPEN = "OPEN", "Open"
        RUNNING = "RUNNING", "Running"
        FINISHED = "FINISHED", "Finished"
        ARCHIVED = "ARCHIVED", "Archived"

    slug = models.SlugField(unique=True, max_length=60)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tournaments",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    time_control = models.CharField(max_length=100, blank=True)
    num_rounds = models.PositiveSmallIntegerField(default=5)
    bye_points = models.DecimalField(max_digits=3, decimal_places=1, default="1.0")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _generate_slug(self.name)
        super().save(*args, **kwargs)
