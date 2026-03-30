"""
Management command to seed the database with test data.
"""

import random
from datetime import date, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from faker import Faker

from apps.appointments.models import Appointment, Review, WorkSchedule
from apps.services.models import Category, MasterService, Service
from apps.users.models import MasterProfile, User

fake = Faker("ru_RU")


class Command(BaseCommand):
    help = "Seed database with test data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing data before seeding",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing data...")
            self.clear_data()

        self.stdout.write("Seeding database...")

        # Create data in order
        categories = self.create_categories()
        services = self.create_services(categories)
        masters = self.create_masters()
        master_services = self.create_master_services(masters, services)
        self.create_work_schedules(masters)
        clients = self.create_clients()
        appointments = self.create_appointments(clients, master_services)
        self.create_reviews(appointments)

        self.stdout.write(self.style.SUCCESS("Database seeded successfully!"))
        self.print_summary()

    def clear_data(self):
        Review.objects.all().delete()
        Appointment.objects.all().delete()
        WorkSchedule.objects.all().delete()
        MasterService.objects.all().delete()
        Service.objects.all().delete()
        Category.objects.all().delete()
        User.objects.filter(role__in=[User.Role.MASTER, User.Role.CLIENT]).delete()

    def create_categories(self):
        self.stdout.write("  Creating categories...")
        categories_data = [
            {
                "name": "Парикмахерские услуги",
                "slug": "hair",
                "description": "Стрижки, укладки, окрашивание и уход за волосами",
                "order": 1,
            },
            {
                "name": "Маникюр и педикюр",
                "slug": "nails",
                "description": "Уход за ногтями, маникюр, педикюр, наращивание",
                "order": 2,
            },
            {
                "name": "Косметология",
                "slug": "cosmetology",
                "description": "Уход за кожей лица и тела, чистки, пилинги",
                "order": 3,
            },
            {
                "name": "Макияж",
                "slug": "makeup",
                "description": "Дневной, вечерний, свадебный макияж",
                "order": 4,
            },
            {
                "name": "Массаж",
                "slug": "massage",
                "description": "Классический, расслабляющий, лечебный массаж",
                "order": 5,
            },
            {
                "name": "Брови и ресницы",
                "slug": "brows-lashes",
                "description": "Оформление бровей, наращивание и ламинирование ресниц",
                "order": 6,
            },
        ]

        categories = []
        for data in categories_data:
            cat, _ = Category.objects.get_or_create(slug=data["slug"], defaults=data)
            categories.append(cat)

        return categories

    def create_services(self, categories):
        self.stdout.write("  Creating services...")
        services_data = {
            "hair": [
                ("Женская стрижка", "zhenskaya-strizhka", 1500, 60, True),
                ("Мужская стрижка", "muzhskaya-strizhka", 800, 30, True),
                ("Детская стрижка", "detskaya-strizhka", 600, 30, False),
                ("Окрашивание в один тон", "okrashivanie-v-odin-ton", 3500, 120, True),
                ("Мелирование", "melirovanie", 4500, 150, False),
                ("Балаяж", "balayazh", 6000, 180, True),
                ("Укладка", "ukladka", 1200, 45, True),
                ("Кератиновое выпрямление", "keratinovoe-vypryamlenie", 8000, 180, False),
                ("Ботокс для волос", "botoks-dlya-volos", 5000, 120, False),
            ],
            "nails": [
                ("Маникюр классический", "manikur-klassicheskiy", 800, 45, True),
                ("Маникюр аппаратный", "manikur-apparatnyy", 1000, 60, True),
                ("Покрытие гель-лак", "pokrytie-gel-lak", 1200, 60, True),
                ("Наращивание ногтей", "narashchivanie-nogtey", 3000, 120, False),
                ("Педикюр классический", "pedikur-klassicheskiy", 1500, 60, True),
                ("Педикюр аппаратный", "pedikur-apparatnyy", 1800, 75, False),
                ("Дизайн ногтей", "dizayn-nogtey", 500, 30, False),
            ],
            "cosmetology": [
                ("Чистка лица ультразвуковая", "chistka-lica-ultrazvukovaya", 2500, 60, True),
                ("Чистка лица механическая", "chistka-lica-mehanicheskaya", 3000, 90, False),
                ("Пилинг химический", "piling-himicheskiy", 3500, 45, True),
                ("Биоревитализация", "biorevitalizaciya", 8000, 60, False),
                ("Мезотерапия лица", "mezoterapiya-lica", 5000, 45, False),
                ("Уходовая процедура", "uhodovaya-procedura", 2000, 60, True),
            ],
            "makeup": [
                ("Дневной макияж", "dnevnoy-makiyazh", 2000, 45, True),
                ("Вечерний макияж", "vecherniy-makiyazh", 3000, 60, True),
                ("Свадебный макияж", "svadebnyy-makiyazh", 5000, 90, True),
                ("Макияж + причёска", "makiyazh-pricheska", 7000, 150, False),
            ],
            "massage": [
                ("Массаж классический (60 мин)", "massazh-klassicheskiy-60", 2500, 60, True),
                ("Массаж классический (90 мин)", "massazh-klassicheskiy-90", 3500, 90, False),
                ("Массаж расслабляющий", "massazh-rasslablyayushchiy", 3000, 60, True),
                ("Массаж антицеллюлитный", "massazh-anticellyulitnyy", 3500, 60, False),
                ("Массаж лица", "massazh-lica", 1500, 30, True),
                ("Массаж спины", "massazh-spiny", 1800, 30, False),
            ],
            "brows-lashes": [
                ("Коррекция бровей", "korrekciya-brovey", 600, 30, True),
                ("Окрашивание бровей", "okrashivanie-brovey", 500, 20, True),
                ("Ламинирование бровей", "laminirovanie-brovey", 1500, 45, True),
                ("Наращивание ресниц классика", "narashchivanie-resnic-klassika", 2500, 120, True),
                ("Наращивание ресниц 2D", "narashchivanie-resnic-2d", 3000, 150, False),
                ("Ламинирование ресниц", "laminirovanie-resnic", 2000, 60, True),
            ],
        }

        services = []
        for category in categories:
            cat_services = services_data.get(category.slug, [])
            for name, slug, price, duration, is_popular in cat_services:
                service, _ = Service.objects.get_or_create(
                    slug=slug,
                    defaults={
                        "category": category,
                        "name": name,
                        "description": fake.paragraph(nb_sentences=2),
                        "price": Decimal(str(price)),
                        "duration": duration,
                        "is_popular": is_popular,
                        "is_active": True,
                    },
                )
                services.append(service)

        return services

    def create_masters(self):
        self.stdout.write("  Creating masters...")
        masters_data = [
            {
                "first_name": "Анна",
                "last_name": "Петрова",
                "specialization": "Парикмахер-стилист",
                "bio": "Опыт работы более 10 лет. Специализируюсь на сложном окрашивании и стрижках.",
                "experience_years": 10,
            },
            {
                "first_name": "Мария",
                "last_name": "Иванова",
                "specialization": "Мастер маникюра",
                "bio": "Сертифицированный мастер маникюра и педикюра. Работаю с любыми покрытиями.",
                "experience_years": 7,
            },
            {
                "first_name": "Елена",
                "last_name": "Сидорова",
                "specialization": "Косметолог",
                "bio": "Врач-косметолог с медицинским образованием. Провожу инъекционные и аппаратные процедуры.",
                "experience_years": 12,
            },
            {
                "first_name": "Ольга",
                "last_name": "Козлова",
                "specialization": "Визажист",
                "bio": "Профессиональный визажист. Работала на показах мод и фотосессиях.",
                "experience_years": 8,
            },
            {
                "first_name": "Наталья",
                "last_name": "Смирнова",
                "specialization": "Массажист",
                "bio": "Дипломированный массажист. Владею различными техниками массажа.",
                "experience_years": 6,
            },
            {
                "first_name": "Светлана",
                "last_name": "Новикова",
                "specialization": "Бровист-лэшмейкер",
                "bio": "Мастер по бровям и ресницам. Создаю идеальный взгляд для каждой клиентки.",
                "experience_years": 5,
            },
            {
                "first_name": "Татьяна",
                "last_name": "Морозова",
                "specialization": "Парикмахер-колорист",
                "bio": "Специализируюсь на сложных техниках окрашивания: балаяж, шатуш, airtouch.",
                "experience_years": 9,
            },
            {
                "first_name": "Ирина",
                "last_name": "Волкова",
                "specialization": "Мастер ногтевого сервиса",
                "bio": "Мастер по наращиванию и дизайну ногтей. Призёр конкурсов nail-art.",
                "experience_years": 6,
            },
        ]

        # Transliteration map for Russian names
        translit_map = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
            'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
        }

        def transliterate(text):
            result = ''
            for char in text.lower():
                result += translit_map.get(char, char)
            return result

        masters = []
        for data in masters_data:
            email = f"{transliterate(data['first_name'])}.{transliterate(data['last_name'])}@belvra.ru"
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": data["first_name"],
                    "last_name": data["last_name"],
                    "phone": fake.phone_number(),
                    "role": User.Role.MASTER,
                    "is_active": True,
                    "is_verified": True,
                },
            )
            if created:
                user.set_password("master123")
                user.save()

            # Update master profile
            profile = user.master_profile
            profile.specialization = data["specialization"]
            profile.bio = data["bio"]
            profile.experience_years = data["experience_years"]
            profile.rating = round(random.uniform(4.0, 5.0), 1)
            profile.reviews_count = random.randint(10, 100)
            profile.is_available = True
            profile.save()
            masters.append(profile)

        return masters

    def create_master_services(self, masters, services):
        self.stdout.write("  Creating master services...")
        # Map masters to service categories
        master_specializations = {
            "Парикмахер-стилист": ["hair"],
            "Парикмахер-колорист": ["hair"],
            "Мастер маникюра": ["nails"],
            "Мастер ногтевого сервиса": ["nails"],
            "Косметолог": ["cosmetology"],
            "Визажист": ["makeup"],
            "Массажист": ["massage"],
            "Бровист-лэшмейкер": ["brows-lashes"],
        }

        master_services = []
        for master in masters:
            categories = master_specializations.get(master.specialization, [])
            for service in services:
                if service.category.slug in categories:
                    ms, _ = MasterService.objects.get_or_create(
                        master=master,
                        service=service,
                        defaults={
                            "price": None,  # Use service default price
                            "duration": None,  # Use service default duration
                        },
                    )
                    master_services.append(ms)

        return master_services

    def create_work_schedules(self, masters):
        self.stdout.write("  Creating work schedules...")
        for master in masters:
            # Create schedule for weekdays (Mon-Fri: 9:00-19:00, Sat: 10:00-17:00)
            for weekday in range(6):  # 0-5 (Mon-Sat)
                if weekday < 5:  # Weekdays
                    start = time(9, 0)
                    end = time(19, 0)
                else:  # Saturday
                    start = time(10, 0)
                    end = time(17, 0)

                WorkSchedule.objects.get_or_create(
                    master=master,
                    weekday=weekday,
                    defaults={
                        "start_time": start,
                        "end_time": end,
                        "is_working": True,
                    },
                )

    def create_clients(self):
        self.stdout.write("  Creating clients...")
        clients = []
        for i in range(15):
            email = fake.unique.email()
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": fake.first_name_female(),
                    "last_name": fake.last_name_female(),
                    "phone": fake.phone_number(),
                    "role": User.Role.CLIENT,
                    "is_active": True,
                    "is_verified": True,
                },
            )
            if created:
                user.set_password("client123")
                user.save()
            clients.append(user)

        return clients

    def create_appointments(self, clients, master_services):
        self.stdout.write("  Creating appointments...")
        appointments = []
        statuses = [
            Appointment.Status.COMPLETED,
            Appointment.Status.COMPLETED,
            Appointment.Status.COMPLETED,
            Appointment.Status.CONFIRMED,
            Appointment.Status.PENDING,
        ]

        # Past appointments (completed)
        for i in range(30):
            ms = random.choice(master_services)
            client = random.choice(clients)
            days_ago = random.randint(1, 60)
            appt_date = date.today() - timedelta(days=days_ago)
            hour = random.randint(9, 17)

            appointment, created = Appointment.objects.get_or_create(
                master=ms.master,
                client=client,
                service=ms.service,
                date=appt_date,
                start_time=time(hour, 0),
                defaults={
                    "end_time": time(hour + 1, 0),
                    "status": Appointment.Status.COMPLETED,
                    "price": ms.actual_price,
                    "notes": fake.sentence() if random.random() > 0.7 else "",
                },
            )
            if created:
                appointments.append(appointment)

        # Future appointments
        for i in range(15):
            ms = random.choice(master_services)
            client = random.choice(clients)
            days_ahead = random.randint(1, 14)
            appt_date = date.today() + timedelta(days=days_ahead)
            hour = random.randint(9, 17)

            appointment, created = Appointment.objects.get_or_create(
                master=ms.master,
                client=client,
                service=ms.service,
                date=appt_date,
                start_time=time(hour, 0),
                defaults={
                    "end_time": time(hour + 1, 0),
                    "status": random.choice(
                        [Appointment.Status.CONFIRMED, Appointment.Status.PENDING]
                    ),
                    "price": ms.actual_price,
                    "notes": fake.sentence() if random.random() > 0.7 else "",
                },
            )
            if created:
                appointments.append(appointment)

        return appointments

    def create_reviews(self, appointments):
        self.stdout.write("  Creating reviews...")
        completed = [a for a in appointments if a.status == Appointment.Status.COMPLETED]
        reviews_count = 0

        for appointment in completed:
            if random.random() > 0.3:  # 70% chance of review
                if not Review.objects.filter(appointment=appointment).exists():
                    Review.objects.create(
                        appointment=appointment,
                        rating=random.randint(4, 5),
                        comment=random.choice([
                            "Отличный мастер! Очень довольна результатом.",
                            "Всё понравилось, обязательно приду ещё!",
                            "Профессионально и качественно. Рекомендую!",
                            "Прекрасная работа, спасибо!",
                            "Замечательный сервис и приятная атмосфера.",
                            "Мастер своего дела! Буду записываться снова.",
                            "Очень аккуратная работа, результат превзошёл ожидания.",
                            "Приятный мастер, качественная работа.",
                            "",  # Some reviews without comments
                        ]),
                    )
                    reviews_count += 1

        self.stdout.write(f"  Created {reviews_count} reviews")

    def print_summary(self):
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("Summary:")
        self.stdout.write(f"  Categories: {Category.objects.count()}")
        self.stdout.write(f"  Services: {Service.objects.count()}")
        self.stdout.write(f"  Masters: {MasterProfile.objects.count()}")
        self.stdout.write(f"  Master Services: {MasterService.objects.count()}")
        self.stdout.write(f"  Work Schedules: {WorkSchedule.objects.count()}")
        self.stdout.write(f"  Clients: {User.objects.filter(role=User.Role.CLIENT).count()}")
        self.stdout.write(f"  Appointments: {Appointment.objects.count()}")
        self.stdout.write(f"  Reviews: {Review.objects.count()}")
        self.stdout.write("=" * 50)
