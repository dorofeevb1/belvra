from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0002_chatmessage_file'),
    ]

    operations = [
        migrations.AlterField(
            model_name='chatmessage',
            name='message_type',
            field=models.CharField(
                choices=[
                    ('text', 'Текст'),
                    ('image', 'Изображение'),
                    ('file', 'Файл'),
                    ('audio', 'Аудио'),
                ],
                default='text',
                max_length=10,
                verbose_name='Тип сообщения'
            ),
        ),
    ]
