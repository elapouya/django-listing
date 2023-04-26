from django.core.management.base import BaseCommand, CommandError
from demo.models import *
from demo.data import *
from datetime import datetime
from django.conf import settings
from django.contrib.auth.models import User
from django_robohash.robotmaker import make_robot_svg
import os
import random


class Command(BaseCommand):
    help = 'Inject test data to database'

    def handle(self, *args, **options):

        interests_objs = {}
        for i,rec in enumerate(interests,start=1):
            self.stdout.write('INTEREST {} of {} : {name}'.format(i,len(interests),**rec))
            obj, created = Interest.objects.get_or_create(**rec)
            interests_objs[rec['name']] = obj

        os.makedirs(settings.FULL_UPLOAD_DIR, exist_ok=True)
        companies_objs = {}
        for i,rec in enumerate(companies):
            self.stdout.write('COMPANY : {name}'.format(**rec))
            obj, created = Company.objects.get_or_create(**rec)
            companies_objs[rec['name']] = obj
            obj.logo.name = 'uploads/company_{}.svg'.format(rec['name'].lower())
            obj.save(force_update=True)
            path = os.path.join(settings.FULL_UPLOAD_DIR,
                                'company_{}.svg'.format(rec['name'].lower()))
            self.stdout.write('Generating {} ...'.format(path))
            if i==1:
                path += '.renamed_for_testing_missing'
            with open(path,'w') as fh:
                fh.write(make_robot_svg(rec['name'],60,60))
        nb_employees = len(employees)
        ranks = list(range(1,nb_employees+1))
        random.shuffle(ranks)
        for i,rec in enumerate(employees,start=1):
            self.stdout.write('EMPLOYEE {} of {} : {first_name} {last_name}'
                              .format(i,len(employees),**rec))
            rec['company'] = companies_objs[rec['company']]
            interests_list = [interests_objs[i] for i in rec['interests'].split(',')]
            del rec['interests']
            rec['address'] = rec['address'].replace(',',',\n').replace('\n ','\n')+'\nUSA'
            rec['rank'] = ranks[i-1]
            emloyee, created = Employee.objects.get_or_create(**rec)
            emloyee.interests.add(*interests_list)
            emloyee.save()

        self.stdout.write('Creating BooleanModel entries...')
        BooleanModel.objects.create(my_bool=True, my_yes_no='y')
        BooleanModel.objects.create(my_bool=True, my_yes_no='n')
        BooleanModel.objects.create(my_bool=False, my_yes_no='y')
        BooleanModel.objects.create(my_bool=False, my_yes_no='n')

        self.stdout.write('Creating admin user...')
        user = User.objects.create_user(username='demo',
                                        password='demo',
                                        is_staff=True,
                                        is_superuser=True)
        self.stdout.write(self.style.WARNING('To access admin site use : demo/demo'))

        self.stdout.write(self.style.SUCCESS('Done.'))