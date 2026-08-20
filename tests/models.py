#
# Models used only by the test suite
#
from django.db import models


class Author(models.Model):
    name = models.CharField(max_length=50)


class Book(models.Model):
    title = models.CharField(max_length=50)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name="books")
    category = models.CharField(max_length=10)


class Review(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="reviews")
    stars = models.IntegerField()
