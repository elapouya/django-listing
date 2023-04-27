# Generated by Django 3.0.5 on 2020-04-29 13:17

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="BooleanModel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("my_bool", models.BooleanField()),
                (
                    "my_yes_no",
                    models.CharField(
                        choices=[("y", "YES"), ("n", "NO")], default="n", max_length=2
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Company",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=60, verbose_name="Name")),
                ("address", models.CharField(max_length=128, verbose_name="Address")),
                ("city", models.CharField(max_length=60, verbose_name="City")),
                ("country", models.CharField(max_length=30, verbose_name="Country")),
                ("phone", models.CharField(max_length=20, verbose_name="Phone")),
                ("email", models.EmailField(max_length=254, verbose_name="e-mail")),
                ("website", models.URLField(verbose_name="Web site")),
                ("logo", models.FileField(upload_to="uploads")),
            ],
        ),
        migrations.CreateModel(
            name="Interest",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=60, verbose_name="Name")),
                (
                    "description",
                    models.CharField(max_length=255, verbose_name="Description"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Employee",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "first_name",
                    models.CharField(max_length=60, verbose_name="First name"),
                ),
                (
                    "last_name",
                    models.CharField(max_length=60, verbose_name="Last name"),
                ),
                ("address", models.TextField(verbose_name="Address")),
                ("age", models.IntegerField(verbose_name="Age")),
                (
                    "designation",
                    models.CharField(max_length=30, verbose_name="Designation"),
                ),
                ("salary", models.IntegerField(verbose_name="Salary")),
                ("joined", models.DateField(null=True, verbose_name="Joined on")),
                (
                    "gender",
                    models.CharField(
                        choices=[("Male", "Male"), ("Female", "Female")],
                        max_length=10,
                        verbose_name="Gender",
                    ),
                ),
                (
                    "marital_status",
                    models.CharField(
                        choices=[("Married", "Married"), ("Unmarried", "Unmarried")],
                        max_length=10,
                        verbose_name="Marital status",
                    ),
                ),
                ("have_car", models.BooleanField()),
                ("rank", models.IntegerField(verbose_name="Rank")),
                (
                    "company",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="demo.Company",
                        verbose_name="Company",
                    ),
                ),
                (
                    "interests",
                    models.ManyToManyField(
                        to="demo.Interest", verbose_name="Interests"
                    ),
                ),
            ],
        ),
    ]