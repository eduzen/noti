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
- **Celery 5.5** - Async task processing
- **Redis** - Message broker and cache
- **PostgreSQL** - Primary database
- **httpx** - HTTP/2 client for APNs
- **Docker Compose** - Local development

## Project Structure

```
noti/
├── core/                    # Main Django project
│   ├── core/               # Settings and configuration
│   │   ├── settings.py     # Django settings
│   │   ├── celery.py       # Celery configuration
│   │   └── urls.py         # URL routing
│   ├── notifications/       # Notifications app
│   │   ├── models.py       # Device and PushNotification models
│   │   ├── serializers.py  # DRF serializers
│   │   ├── views.py        # API viewsets
│   │   ├── tasks.py        # Celery tasks for sending notifications
│   │   ├── admin.py        # Django admin configuration
│   │   └── urls.py         # App URL routing
│   └── manage.py
├── docker-compose.yml       # PostgreSQL + Redis
├── pyproject.toml          # Dependencies
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

### Device

Tracks registered iOS devices:
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

# Database (use sqlite for dev, postgresql for prod)
DB_ENGINE=sqlite
# DB_ENGINE=postgresql

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0

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
   - Use PostgreSQL (`DB_ENGINE=postgresql`)
   - Configure connection pooling
   - Set up backups

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

- **Horizontal**: Add more Celery workers
- **Vertical**: Increase worker concurrency
- **Database**: Add read replicas, connection pooling
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
