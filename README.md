# AirsoftPlace
#### Специализированный маркетплейс страйкбольного оборудования

- [Локальный запуск с Docker Compose](#Docker_Compose)
  - [Тестирование при запуске с Docker Compose](#Docker_Compose_testing)
- [Локальный запуск без Docker (упрощенная версия системы)](#No_Docker_Compose)
  - [Тестирование при запуске без Docker](#No_Docker_Compose_testing)
- [Автоматизированное тестирование](#Autotesting)

## Локальный запуск с Docker Compose <a name="Docker_Compose"></a> 
- В airsoft-marketplace/proj (рядом с файлом manage.py) разместить .env файл (или просто скопировать .env.example и переименовать в .env). Env переменные:
```  
EMAIL_HOST='mailhog'
EMAIL_HOST_USER='airsoftplace-test-no-reply@outlook.com'
EMAIL_HOST_PASSWORD=''
EMAIL_PORT=1025
MANAGER_EMAIL='airsoftplace-test@outlook.com'
SECRET_KEY='some_secret_key'
DB_ENGINE='django.db.backends.postgresql'
DB_NAME='proj_db'
DB_USER='pguser'
DB_PASSWORD='pgpassword'
DB_HOST='db'
DB_PORT=5432
REDIS_URL="redis://redis/1"
CELERY_BROKER_URL="redis://redis/0"
EMAIL_USE_TLS='False'
ALLOWED_HOSTS = '127.0.0.1 localhost'
DEBUG='False'
YOOKASSA_SECRET_KEY='SECRET_KEY'
YOOKASSA_SHOP_ID='SHOP_ID'
```
- Для работы сторонней кассы [создать тестовый магазин в ЮKassa](https://yookassa.ru/docs/support/merchant/payments/implement/test-store) и присвоить переменным YOOKASSA_SECRET_KEY и YOOKASSA_SHOP_ID в .env-файле его ключ и id (можно пропустить, но тогда оплата и создание заказов будут невозможны)

- Через консоль перейти в папку проекта (airsoft-marketplace) и создать образ
```console  
docker compose build web
```
- Выполнить команду для миграций
```console  
docker compose run --rm web python manage.py migrate
``` 
- Запустить проект
```console  
docker compose up
```
- Собрать статические файлы
```console  
docker-compose exec web python manage.py collectstatic --no-input
```
- Заполнить БД демонстрационным набором данных из JSON-фикстуры "all_data.json"
```console  
docker compose run --rm web python manage.py loaddata all_data.json
```
Отобразится по адресу http://localhost:8000/.

Админка - http://localhost:8000/admin/ (Логин - Admin , Пароль - Password )

Mailhog (тестовый почтовый сервер, мониторинг исходящих) - http://localhost:8025/

Flower (мониторинг задач celery) - http://localhost:5555/

- Для корректной обработки событий успешной и отклоненной оплаты в сторонней кассе (обновление статуса заказа и отображение в списке заказов магазина, уменьшение количества товаров у продавца, обновление отчета о продажах магазина, уведомление продаца и клиента об успешном заказе - при успешной, удаление заказа - при отклоненной) необходимо [настроить отправку HTTP-уведомлений в ЮKassa](https://yookassa.ru/developers/using-api/webhooks) на URL вебхука из приложения cart (cart/webhook-yookassa/). При локальном запуске пропускается, обработка событий оплаты [проверяется в модульных и интеграционных тестах](#Docker_Compose_testing) с помощью моков.

### Тестирование при запуске с Docker Compose <a name="Docker_Compose_testing"></a> 
- Для запуска всех модульных и интеграционных тестов  
```console  
docker compose run --rm web pytest
```


## Локальный запуск без Docker (упрощенная версия системы) <a name="No_Docker_Compose"></a> 
Запуск на Django-сервере, БД - SQLite, кэш - LocMemCache, асинхронные задачи - синхронны, письма создаются в виде файлов в папке sent_emails.

- Желательно иметь версию Python 3.12

- В airsoft-marketplace/proj (рядом с файлом manage.py) разместить .env файл (или просто скопировать .env.example и переименовать в .env). Env переменные:
```  
EMAIL_HOST='mailhog'
EMAIL_HOST_USER='airsoftplace-test-no-reply@outlook.com'
EMAIL_HOST_PASSWORD=''
EMAIL_PORT=1025
MANAGER_EMAIL='airsoftplace-test@outlook.com'
SECRET_KEY='some_secret_key'
DB_ENGINE='django.db.backends.postgresql'
DB_NAME='proj_db'
DB_USER='pguser'
DB_PASSWORD='pgpassword'
DB_HOST='db'
DB_PORT=5432
REDIS_URL="redis://redis/1"
CELERY_BROKER_URL="redis://redis/0"
EMAIL_USE_TLS='False'
ALLOWED_HOSTS = '127.0.0.1 localhost'
DEBUG='False'
YOOKASSA_SECRET_KEY='SECRET_KEY'
YOOKASSA_SHOP_ID='SHOP_ID'
```
- Для работы сторонней кассы [создать тестовый магазин в ЮKassa](https://yookassa.ru/docs/support/merchant/payments/implement/test-store) и присвоить переменным YOOKASSA_SECRET_KEY и YOOKASSA_SHOP_ID в .env-файле его ключ и id (можно пропустить, но тогда оплата и создание заказов будут невозможны)

- Через консоль перейти в папку проекта (airsoft-marketplace), установить и активировать виртуальное окружение
```console  
python -m venv venv
```
или
```console  
python3 -m venv venv
```
активация Windows:
```console  
.\venv\Scripts\activate.bat
```
активация macOS и Linux:
```console  
source venv/bin/activate
```
- Установить в виртуальное окружение используемые библиотеки
```console  
pip install -r requirements.txt
``` 
- Через консоль перейти в папку airsoft-marketplace/proj (папка с файлом manage.py) и собрать статические файлы
```console  
python manage.py collectstatic --no-input --settings=proj.settings_test
```
или
```console  
python3 manage.py collectstatic --no-input --settings=proj.settings_test
```
- В папке с файлом manage.py выполнить команду для запуска локального сервера (SQLite с демонстрационными данными уже в каталоге):
```console  
python manage.py runserver  --settings=proj.settings_test
```
или
```console  
python3 manage.py runserver  --settings=proj.settings_test
```
Отобразится по адресу http://127.0.0.1:8000/.

Админка - http://127.0.0.1:8000/admin/ (Логин - Admin , Пароль - Password )

- Для корректной обработки событий успешной и отклоненной оплаты в сторонней кассе (обновление статуса заказа и отображение в списке заказов магазина, уменьшение количества товаров у продавца, обновление отчета о продажах магазина, уведомление продаца и клиента об успешном заказе - при успешной, удаление заказа - при отклоненной) необходимо [настроить отправку HTTP-уведомлений в ЮKassa](https://yookassa.ru/developers/using-api/webhooks) на URL вебхука из приложения cart (cart/webhook-yookassa/). При локальном запуске пропускается, обработка событий оплаты [проверяется в модульных и интеграционных тестах](#No_Docker_Compose_testing) с помощью моков.

### Тестирование при запуске без Docker <a name="No_Docker_Compose_testing"></a> 
- Для запуска всех модульных и интеграционных тестов в папке airsoft-marketplace/proj (папка с файлом manage.py) выполнить команду 
```console  
pytest
```

## Автоматизированное тестирование <a name="Autotesting"></a> 
В проекте реализовано автоматизированное тестирование через GitHub Actions. При загрузке в репозиторий происходит запуск всех модульных и интеграционных тестов, а также проверка соответствия кода нормам PEP8 через flake8. Результаты тестирования представлены в репозитории.
