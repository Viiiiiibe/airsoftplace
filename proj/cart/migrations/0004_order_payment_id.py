# Generated by Django 5.0.2 on 2025-03-09 19:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cart', '0003_alter_orderitem_product'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='payment_id',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='ID платежа'),
        ),
    ]
