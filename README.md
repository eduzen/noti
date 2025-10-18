# Noti - iOS Push Notification Service

A production-ready Django REST API for sending iOS push notifications at scale. Built to handle 200k+ notifications per day with reliability and performance in mind.

## Features

- **RESTful API** - Clean DRF-based API for sending push notifications
- **Async Processing** - Celery + Redis for reliable background job processing
- **Scalable** - Designed to handle burst traffic (100k+ notifications in 2-hour windows)
- **Reliable** - Database tracking, retry logic, and comprehensive error handling
- **Device Management** - Track device tokens and their status
- **Admin Interface** - Django admin for monitoring and management
- **API Documentation** - Auto-generated OpenAPI/Swagger docs

## Architecture

```
External Services → Django API → Redis Queue → Celery Workers → APNs
                                       ↓
                                  PostgreSQL (tracking & reliability)
```

## Tech Stack

- **Django 5.2** + **Django REST Framework**
- **PostgreSQL** with **psycopg 3** - Native connection pooling (Django 5.1+)
- **Celery 5.5** - Async task processing
- **Redis** - Message broker and cache
- **Custom User Model** - Email-based authentication
- **httpx** - HTTP/2 client for APNs
- **Docker Compose** - Local development

## Project Structure

```
noti/
├── accounts/                # Authentication app
│   ├── models.py           # Custom User + UserProfile models
│   └── admin.py            # User admin with inline profile
├── notifications/           # Notifications app
│   ├── models.py           # DeviceOwner, Device, PushNotification
│   ├── serializers.py      # DRF serializers
│   ├── views.py            # API viewsets
│   ├── tasks.py            # Celery tasks for sending notifications
│   ├── admin.py            # Django admin configuration
│   └── urls.py             # App URL routing
├── core/                    # Django project settings
│   ├── settings.py         # Django settings
│   ├── celery.py           # Celery configuration
│   └── urls.py             # URL routing
├── manage.py
├── docker-compose.yml       # 5 services (PostgreSQL, Redis, Web, Celery Worker, Celery Beat)
├── pyproject.toml          # Dependencies (uv)
└── .env.example            # Environment variables template
```

## Quick Start

### Option 1: Docker (Recommended)

**Prerequisites:**
- Docker and Docker Compose
- Just (optional, for convenient commands)

**Setup with Docker:**

```bash
# Build and start all services (Django, Celery, PostgreSQL, Redis)
docker-compose up -d

# Or use just commands
just build  # Build images
just up     # Start all services

# Run migrations
docker-compose exec web uv run python manage.py migrate
# Or: just docker-migrate

# Create superuser
docker-compose exec web uv run python manage.py createsuperuser
# Or: just docker-createsuperuser

# View logs
docker-compose logs -f
# Or: just logs

# View specific service logs
just logs web
just logs celery_worker
```

**That's it!** Your entire stack is now running:
- Django API: http://localhost:8000
- API Docs: http://localhost:8000/api/docs/
- Admin: http://localhost:8000/admin/
- PostgreSQL: localhost:5432
- Redis: localhost:6379

**Useful Docker commands:**
```bash
just ps              # View running services
just down            # Stop all services
just restart web     # Restart a service
just bash            # Access Django container
just docker-shell    # Django shell
```

### Option 2: Local Development (Without Docker)

**Prerequisites:**
- Python 3.14+
- Docker Compose (for PostgreSQL and Redis only)
- uv (Python package manager)

**Setup:**

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
# Or: just install

# Start only infrastructure (PostgreSQL + Redis)
docker-compose up -d postgres redis
# Or: just infra

# Configure environment (optional for local dev with SQLite)
cp .env.example core/.env

# Run migrations
cd core
uv run python manage.py migrate
# Or: just migrate

# Create superuser
uv run python manage.py createsuperuser
```

**Start services (3 separate terminals):**

Terminal 1 - Django:
```bash
cd core
uv run python manage.py runserver
# Or: just runserver
```

Terminal 2 - Celery Worker:
```bash
cd core
uv run celery -A core worker -l info
# Or: just worker
```

Terminal 3 - Celery Beat (optional):
```bash
cd core
uv run celery -A core beat -l info
# Or: just beat
```

## API Endpoints

### Base URL
- Local: `http://localhost:8000/api/`

### Endpoints

#### Device Management

**Register/Update Device**
```bash
POST /api/devices/
{
    "device_token": "your-device-token-here",
    "platform": "ios",
    "is_active": true
}
```

**List Devices**
```bash
GET /api/devices/
```

#### Push Notifications

**Send Single Notification**
```bash
POST /api/notifications/
{
    "device_token": "your-device-token",
    "title": "Hello",
    "body": "This is a test notification",
    "badge": 1,
    "sound": "default",
    "data": {
        "custom_key": "custom_value"
    }
}
```

**Send Bulk Notifications**
```bash
POST /api/notifications/bulk/
{
    "device_tokens": ["token1", "token2", "token3"],
    "title": "Bulk Notification",
    "body": "Sent to multiple devices",
    "badge": 1
}
```

**List Notifications**
```bash
GET /api/notifications/
GET /api/notifications/?status=sent
GET /api/notifications/?device_token=xxx
```

**Get Notification Stats**
```bash
GET /api/notifications/stats/
```

### API Documentation

- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **OpenAPI Schema**: http://localhost:8000/api/schema/

## Database Models

### User (Custom Auth Model)

Email-based authentication for Django admin/staff:
- `email` - Unique email (used as username)
- `password` - Hashed password
- `is_staff`, `is_active`, `is_superuser` - Permissions
- `created_at`, `updated_at` - Timestamps

### UserProfile

Personal information (one-to-one with User):
- `first_name`, `last_name`, `phone` - Personal details

### DeviceOwner

iOS app users who own devices (NOT Django login users):
- `external_id` - Unique identifier from your iOS app
- `email`, `name` - Optional personal information
- `is_active` - Whether owner is active

### Device

Registered iOS/Android devices:
- `owner` - ForeignKey to DeviceOwner
- `device_token` - Unique device identifier
- `platform` - ios/android (future-proof)
- `is_active` - Whether device can receive notifications
- `last_notification_at` - Last successful notification timestamp

### PushNotification

Individual notification records:
- Target: `device`, `device_token`
- Content: `title`, `body`, `badge`, `sound`, `category`, `data`
- Status: `pending`, `queued`, `sending`, `sent`, `failed`, `invalid_token`
- Tracking: `retry_count`, `created_at`, `sent_at`, `apns_id`

## Configuration

### Environment Variables

See `.env.example` for all available options. Key variables:

```bash
# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database - PostgreSQL with Django 5.1+ connection pooling (psycopg 3)
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/noti
# For local development:
# DATABASE_URL=postgresql://postgres:postgres@localhost:5432/noti

# PostgreSQL Container (for docker-compose)
POSTGRES_DB=noti
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# Celery
CELERY_BROKER_URL=redis://redis:6379/0

# APNs
APNS_KEY_ID=your-key-id
APNS_TEAM_ID=your-team-id
APNS_BUNDLE_ID=com.yourcompany.yourapp
APNS_USE_SANDBOX=True
```

### APNs Setup

To send real notifications, you need:

1. Apple Developer account
2. APNs Auth Key or Certificate
3. Update `core/notifications/tasks.py:150` with proper APNs authentication

See [Apple's documentation](https://developer.apple.com/documentation/usernotifications) for details.

## Development

### Run Tests

```bash
cd core
uv run pytest
```

### Django Admin

Access at http://localhost:8000/admin/

The admin interface provides:
- Device management with status tracking
- Notification history with colored status badges
- Filtering and search capabilities
- Detailed notification inspection

### Database Migrations

```bash
cd core
uv run python manage.py makemigrations
uv run python manage.py migrate
```

## Production Deployment

### Checklist

1. **Environment**
   - Set `DEBUG=False`
   - Generate new `SECRET_KEY`
   - Configure `ALLOWED_HOSTS`

2. **Database**
   - Set production `DATABASE_URL` (PostgreSQL)
   - Django 5.1+ native connection pooling already configured (psycopg[pool])
   - Set up backups and monitoring

3. **Redis**
   - Use persistent Redis instance
   - Configure maxmemory policy
   - Enable AOF persistence

4. **Celery**
   - Use supervisor/systemd for worker management
   - Scale workers based on load
   - Set up monitoring (Flower, Prometheus)

5. **Web Server**
   - Use gunicorn behind nginx
   - Configure static files
   - Set up SSL/TLS

6. **APNs**
   - Use production APNs endpoint
   - Implement proper JWT/certificate auth in `tasks.py`

### Scaling

- **Horizontal**: Add more Celery workers (`docker-compose up -d --scale celery_worker=5`)
- **Vertical**: Increase worker concurrency
- **Database**: Add read replicas (connection pooling already configured)
- **Redis**: Use Redis Cluster for > 1M notifications/day

## Monitoring

Key metrics to track:
- Notification success/failure rates
- Queue depth and processing time
- Invalid token rate
- API response times
- Database connection pool usage

## Troubleshooting

**Celery worker not processing tasks**
- Check Redis connection
- Verify worker is running
- Check worker logs for errors

**Notifications stuck in 'queued' status**
- Celery worker may be down
- Check task logs in Django admin
- Verify APNs credentials

**High failure rate**
- Check APNs credentials
- Verify device tokens are valid
- Check error messages in admin

## License

MIT

## Support

For issues and questions, please open a GitHub issue.
