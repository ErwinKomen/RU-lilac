"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

import django
django.setup()                      # This is needed apparently
from django.test import TestCase
from django.urls import reverse
from solemne.seeker.models import City, Country


# TODO: Configure your database in settings.py and sync before running tests.

class SimpleTest(TestCase):
    """Tests for the application views."""

    # NOTE: this is not needed anymore since Django 1.8
    #       https://stackoverflow.com/questions/29653129/update-to-django-1-8-attributeerror-django-test-testcase-has-no-attribute-cl
    # Django requires an explicit setup() when running tests in PTVS
    #@classmethod
    #def setUpTestData(cls):
    #    django.setup()

    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

class CityTestCase(TestCase):
    """Test anything related to CITY per se"""

    def create_city(self, name, country=None):
        """Create an element in the City table"""

        obj = None
        if country != None and isinstance(country, str) and country != "":
            obj_country = Country.objects.filter(name__iexact=country).first()
            if obj_country != None:
                obj = City.objects.create(name=name, country=obj_country)
        if obj == None:
            obj = City.objects.create(name=name)
        return obj

    def remove_city(self, name):
        obj = City.objects.filter(name__iexact=name).first()
        if obj != None:
            obj.remove()

    def remove_country(self, name):
        obj = Country.objects.fitler(name__iexaxt=name).first()
        if obj != None:
            obj.remove()

    def setUp(self):
        self.remove_city("panorama")
        self.remove_city("Zelfbedacht")
        self.create_city("panorama")
        self.create_city("Zelfbedacht", "netherlands")

    def test_city_create(self):
        """Test adding a city to the database"""

        c1 = City.objects.get(name__iexact="panorama")
        self.assertNotEqual(c1, None)
        self.assertEqual(c1.name.lower(), "panorama")

        cn = Country.objects.get(name__iexact="netherlands")
        self.assertNotEqual(cn, None)
        self.assertEqual(cn.name.lower(), "netherlands")
        
        c2 = City.objects.get(name__iexact="Zelfbedacht", country=cn)
        self.assertNotEqual(c2, None)
        self.assertEqual(c2.name.lower(), "zelfbedacht")
        self.assertNotEqual(c2.country, None)
        self.assertEqual(c2.country.name.lower(), "netherlands")

class HomePageTests(TestCase):

    def test_home_page_status_code(self):
        response = self.client.get(reverse("home"))
        self.assertEquals(response.status_code, 200)

    def test_home_page_template(self):
        with self.settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}}):
            response = self.client.get(reverse("home"), follow=True)
            self.assertEquals(response.status_code, 200)
            self.assertTemplateUsed(response, 'index.html')
            self.assertTemplateUsed(response, 'layout.html')
            self.assertTemplateUsed(response, 'topnav.html')
