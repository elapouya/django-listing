#
# Created : 2018-02-16
#
# @author: Eric Lapouyade
#

from django.db import models
from django.db.models import Max
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django_better_image.fields import BetterImageOriginalField, BetterImageField
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFill, ResizeToFit


class Company(models.Model):
    name = models.CharField(max_length=60, verbose_name=_('Name'))
    address = models.CharField(max_length=128, verbose_name=_('Address'))
    city = models.CharField(max_length=60, verbose_name=_('City'))
    country = models.CharField(max_length=30, verbose_name=_('Country'))
    phone = models.CharField(max_length=20, verbose_name=_('Phone'))
    email = models.EmailField(verbose_name=_('e-mail'))
    website = models.URLField(verbose_name=_('Web site'))
    logo = models.FileField(upload_to=settings.MEDIA_UPLOAD_DIR)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('company_detail', args=[self.pk])


class Interest(models.Model):
    name = models.CharField(max_length=60, verbose_name=_('Name'))
    description = models.CharField(max_length=255, verbose_name=_('Description'))

    def __str__(self):
        return self.name


class Employee(models.Model):
    GENDER_CHOICES = (
        ('Male',_('Male')),
        ('Female', _('Female')),
    )
    MARITAL_STATUS_CHOICES = (
        ('Married',_('Married')),
        ('Unmarried', _('Unmarried')),
    )
    first_name = models.CharField(max_length=60, verbose_name=_('First name'))
    last_name = models.CharField(max_length=60, verbose_name=_('Last name'))
    address = models.TextField(verbose_name=_('Address'))
    age = models.IntegerField(verbose_name=_('Age'))
    designation = models.CharField(max_length=30, verbose_name=_('Designation'))
    salary = models.IntegerField(verbose_name=_('Salary'))
    # joined = models.DateTimeField(null=True, verbose_name=_('Joined on'))
    joined = models.DateField(null=True, verbose_name=_('Joined on'))
    gender = models.CharField(max_length=10, verbose_name=_('Gender'),
                              choices=GENDER_CHOICES)
    marital_status = models.CharField(max_length=10,
                                      verbose_name=_('Marital status'),
                                      choices=MARITAL_STATUS_CHOICES)
    have_car = models.BooleanField()
    interests = models.ManyToManyField(Interest, verbose_name=_('Interests'))
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True,
                                         verbose_name=_('Company'))
    rank = models.IntegerField(verbose_name=_('Rank'))

    def save(self, *args, **kwargs):
        if not self.rank:
            self.rank = Employee.objects.aggregate(Max('rank')).get('rank__max',0) + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return '{} {}'.format(self.first_name,self.last_name)

    def get_absolute_url(self):
        return reverse('employee_detail', args=[self.pk])


# Just for testing that django-listing is able to recognize boolean fields...
class BooleanModel(models.Model):
    YES_NO_CHOICES = (
        ('y','YES'),
        ('n', 'NO'),
    )
    my_bool = models.BooleanField()
    my_yes_no = models.CharField(max_length=2, choices=YES_NO_CHOICES, default='n')


class ProductImage(models.Model):
    created = models.DateTimeField(
        auto_now_add=True,
        blank=True, null=True,)
    image = models.ImageField(
        upload_to='product_images/%Y/%m/%d/',
        blank=True, null=True)
    image_small_thumb = ImageSpecField(
        source='image',
        processors=[ResizeToFill(75, 75)],
        format='JPEG',
        options={'quality': 50})
    image_medium_thumb = ImageSpecField(
        source='image',
        processors=[ResizeToFill(150, 150)],
        format='JPEG',
        options={'quality': 50})
    image_big_thumb = ImageSpecField(
        source='image',
        processors=[ResizeToFill(300, 300)],
        format='JPEG',
        options={'quality': 30})


class EditableProductImage(models.Model):
    created = models.DateTimeField(
        auto_now_add=True,
        blank=True, null=True,
    )
    title = models.CharField(
        max_length=80,
        blank=True, null=True,
    )
    description = models.TextField()

    # Use django-better-image to have nice image editing
    # and use django-imagekit to have multiple image sizes
    image = BetterImageField(
        upload_to='product_images/%Y/%m/%d/',
        keep_original_in='image_original',
        thumb_name='image_form_thumb',
        thumb_aspect_ratio=1,
        buttons_placement='right',
        use_dropzone=False,
        crop_file_format='JPEG',
        blank=True, null=True)
    image_original = BetterImageOriginalField(
        upload_to='product_images/%Y/%m/%d/',
        blank=True, null=True)
    image_small_thumb = ImageSpecField(
        source='image',
        processors=[ResizeToFill(75, 75)],
        format='JPEG',
        options={'quality': 50})
    image_medium_thumb = ImageSpecField(
        source='image',
        processors=[ResizeToFill(150, 150)],
        format='JPEG',
        options={'quality': 50})
    image_big_thumb = ImageSpecField(
        source='image',
        processors=[ResizeToFill(300, 300)],
        format='JPEG',
        options={'quality': 30})
