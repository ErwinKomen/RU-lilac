# Generated by Django 2.2.24 on 2022-02-17 14:10

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Book',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Name (English)')),
                ('latname', models.CharField(blank=True, max_length=100, null=True, verbose_name='Name (Latin)')),
                ('abbr', models.CharField(max_length=5, verbose_name='Abbreviation (English)')),
                ('latabbr', models.CharField(blank=True, max_length=100, null=True, verbose_name='Abbreviation (Latin)')),
                ('idno', models.IntegerField(default=-1, verbose_name='Identifier')),
                ('chnum', models.IntegerField(default=-1, verbose_name='Number of chapters')),
            ],
        ),
        migrations.CreateModel(
            name='Chapter',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.IntegerField(default=-1, verbose_name='Chapter')),
                ('vsnum', models.IntegerField(default=-1, verbose_name='Number of verses')),
                ('book', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bookchapters', to='bible.Book')),
            ],
        ),
    ]
