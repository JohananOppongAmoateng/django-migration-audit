from django.db import models


class Author(models.Model):
    """A blog author."""

    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    bio = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Post(models.Model):
    """A blog post written by an Author."""

    STATUS_DRAFT = "draft"
    STATUS_PUBLISHED = "published"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_PUBLISHED, "Published"),
    ]

    title = models.CharField(max_length=500)
    slug = models.SlugField(unique=True)
    content = models.TextField()
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name="posts")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # view_count added in migration 0003
    view_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title


class Tag(models.Model):
    """A label that categorises posts."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class PostTag(models.Model):
    """Explicit many-to-many join table between Post and Tag.

    Using an explicit through model (rather than Django's implicit M2M join
    table) keeps the expected schema fully visible in migrations — every table
    has a corresponding CreateModel operation, so the audit tool can verify it
    without needing special M2M handling.

    We will need to support m2m fully later
    """

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="post_tags")
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name="post_tags")

    class Meta:
        unique_together = [("post", "tag")]

    def __str__(self):
        return f"{self.post} — {self.tag}"
