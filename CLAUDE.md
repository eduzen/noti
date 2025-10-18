# Claude Context - Noti Project

This document provides context for AI assistants working on this codebase.

## Project Overview

**Noti** is a production-ready iOS push notification service built with Django REST Framework. It's designed to handle 200,000+ notifications per day with burst traffic patterns (100k+ in 2-hour windows).

### Key Requirements

- **Scale**: 200k notifications/day, with most grouped in 2-hour windows
- **Reliability**: Cannot lose notifications - database tracking + retry logic
- **Readable Code**: Pragmatic, maintainable, not over-engineered
- **Scalable Architecture**: Must scale horizontally

### Architecture Decision: Why Django (not FastAPI)

Initially FastAPI was considered for better async performance, but **Django was chosen** because:
1. User's expertise is in Django
2. Pragmatism over performance (I/O bottleneck is APNs, not serialization)
3. Battle-tested Django + Celery pattern for this exact use case
4. Better admin interface for monitoring
5. Rich ecosystem

## Technology Stack

- **Django 5.2** + **Django REST Framework** - API layer
- **PostgreSQL** with **psycopg[binary,pool] 3.2+** - Native connection pooling (Django 5.1+)
- **Celery 5.5** - Async task processing
- **Redis** - Message broker
- **Custom User Model** - Email-based authentication (no username)
- **Python 3.14** - Latest Python version
- **Docker Compose** - Development environment
- **uv** - Package manager

### Why NOT Django Ninja / Pydantic

Django Ninja was discussed (FastAPI-like syntax with Django) but **DRF was chosen** because:
1. More mature and battle-tested
2. User is familiar with DRF
3. Pydantic vs DRF serialization speed difference is negligible compared to APNs network I/O
4. Pragmatism over micro-optimizations

## Project Structure

```
noti/
├── accounts/                      # Authentication app
│   ├── models.py                 # Custom User + UserProfile models
│   ├── admin.py                  # User admin with inline profile
│   └── migrations/
├── notifications/                 # Main app
│   ├── models.py                 # DeviceOwner, Device, PushNotification
│   ├── serializers.py            # DRF serializers
│   ├── views.py                  # API viewsets
│   ├── tasks.py                  # Celery tasks for APNs
│   ├── admin.py                  # Django admin with colored badges
│   ├── urls.py                   # App URL routing
│   └── migrations/
├── core/                          # Settings module
│   ├── settings.py               # Environment-based configuration
│   ├── celery.py                 # Celery app initialization
│   ├── urls.py                   # Main URL routing
│   └── __init__.py               # Celery app import
├── manage.py
├── Dockerfile                     # Python 3.14-slim based
├── docker-compose.yml             # 5 services (postgres, redis, web, celery_worker, celery_beat)
├── .dockerignore
├── pyproject.toml                 # uv dependency management (psycopg[binary,pool])
├── justfile                       # Convenient commands
└── .env.example                   # Environment template
```

## Core Models

### TimeStampedModel (`notifications/models.py:5`)

**Abstract base model** for consistent timestamps:
- `created_at` - Auto-set on creation (auto_now_add=True)
- `updated_at` - Auto-updated on save (auto_now=True)

**Key Decision**: DRY principle for timestamps
- All models inherit from TimeStampedModel
- Uniform timestamp behavior across the system
- Easy to add common fields to all models in the future

### User Model (`accounts/models.py:32`)

**Custom User model** with email-based authentication (NO username):
- `email` - Unique email field (used as USERNAME_FIELD)
- `password` - Hashed password (from AbstractBaseUser)
- `is_staff`, `is_active`, `is_superuser` - Permission flags
- `created_at`, `updated_at` - Timestamps

**Key Decision**: Minimal authentication-only user model
- Personal information stored in separate UserProfile (one-to-one)
- Separation of concerns: auth vs. profile data
- Cleaner security model

**Custom UserManager**:
- `create_user(email, password)` - Create regular user
- `create_superuser(email, password)` - Create admin user

### UserProfile Model (`accounts/models.py:61`)

Personal information **separate from authentication**:
- `user` - OneToOneField to User (accessed via `user.profile`)
- `first_name`, `last_name` - Personal names
- `phone` - Contact information
- `created_at`, `updated_at` - Timestamps

**Key Decision**: One-to-one pattern for personal data
- Keeps User model minimal and focused on authentication
- Personal data separate from security-critical auth data

### DeviceOwner Model (`notifications/models.py:15`)

**iOS app users** who own devices (NOT Django login users):
- `external_id` - Unique identifier from your iOS app (indexed)
- `email`, `name` - Optional personal information
- `is_active` - Whether owner is active
- `created_at`, `updated_at` - Timestamps (from TimeStampedModel)

**Key Decision**: Separate from User model
- DeviceOwner = iOS app users (cannot log into Django)
- User = Django admin/staff users (can log into Django)
- Clear separation of concerns
- DeviceOwner optimized for 200k+ notifications/day

### Device Model (`notifications/models.py:39`)

Tracks registered iOS devices:
- `owner` - ForeignKey to DeviceOwner (nullable for backward compatibility)
- `device_token` - Unique device identifier (indexed)
- `platform` - ios/android (future-proof)
- `is_active` - Whether device can receive notifications
- `last_notification_at` - Last successful notification timestamp
- `created_at`, `updated_at` - Timestamps (from TimeStampedModel)

**Key Decision**: Device links to DeviceOwner (not User)
- Device ownership tracking
- Device-level analytics per owner
- Multi-device support per owner
- Future multi-platform support

### PushNotification Model (`notifications/models.py:36`)

Individual notification records for **reliability**:
- **Status tracking**: `pending` → `queued` → `sending` → `sent`/`failed`
- **Retry logic**: `retry_count`, `max_retries` (default: 3)
- **Error handling**: `error_message`, `invalid_token` status
- **APNs fields**: `title`, `body`, `badge`, `sound`, `category`, `thread_id`, `data`
- **Audit trail**: `created_at`, `sent_at`, `apns_id`

**Key Decision**: Every notification is stored in DB (not just queued) because:
1. User requirement: "don't lose notifications"
2. Full audit trail for debugging
3. Retry logic needs persistent state
4. Analytics and reporting

### Helper Methods

Models have pragmatic helper methods:
- `notification.mark_as_sent(apns_id)` - Updates status + timestamp
- `notification.mark_as_failed(error)` - Records failure
- `notification.increment_retry()` - Handles retry logic
- `notification.mark_token_invalid()` - Deactivates device

## API Design

### Endpoints (`notifications/views.py`)

#### Device Management
- `POST /api/devices/` - Register/update device (upsert logic)
- `GET /api/devices/` - List devices (filterable)
- `GET /api/devices/{id}/` - Get device
- `PATCH /api/devices/{id}/` - Update device

#### Push Notifications
- `POST /api/notifications/` - Send single notification
- `POST /api/notifications/bulk/` - Send to multiple devices (max 1000)
- `GET /api/notifications/` - List notifications (filterable by status)
- `GET /api/notifications/{id}/` - Get notification details
- `GET /api/notifications/stats/` - Aggregated statistics

### Key Design Decisions

**Upsert for devices** (`views.py:46`):
- `POST /devices/` with existing token updates instead of erroring
- Prevents client-side complexity

**Bulk endpoint limits** (`serializers.py:109`):
- Max 1000 devices per request
- Prevents memory issues
- For larger batches, call multiple times

**Immediate queueing** (`views.py:106`):
- API returns immediately after queueing
- Celery handles actual sending
- Client doesn't wait for APNs response

## Celery Task Architecture

### Task: `send_push_notification` (`notifications/tasks.py:18`)

**Flow**:
1. Fetch notification from DB
2. Mark as `sending`
3. Build APNs payload
4. Send to APNs (via `send_to_apns`)
5. Handle response:
   - Success → `mark_as_sent(apns_id)`
   - Invalid token → `mark_token_invalid()` (deactivates device)
   - Other errors → retry (up to 3 times)

**Retry Configuration**:
- Max retries: 3
- Delay: 60 seconds (exponential backoff possible)
- Bound task (`bind=True`) for retry access

**Error Handling**:
```python
# APNs error reasons that invalidate tokens
if error_reason in ["BadDeviceToken", "Unregistered", "DeviceTokenNotForTopic"]:
    notification.mark_token_invalid()  # No retry
else:
    notification.increment_retry()      # Retry
```

### APNs Integration (`notifications/tasks.py:150`)

**Current State**: Mock implementation for development
- Returns fake success responses
- Logs what would be sent

**Production TODO**:
```python
# Replace send_to_apns() with real APNs HTTP/2 client
# Options:
# 1. Use aioapns library (recommended)
# 2. Use PyAPNs2
# 3. Custom httpx HTTP/2 client with JWT/certificate auth
```

**Authentication Required**:
- JWT token-based (needs: `APNS_KEY_ID`, `APNS_TEAM_ID`)
- OR certificate-based (`.p8` file)

## Configuration

### Environment Variables (`.env.example`)

**Database** (using dj-database-url):
```bash
# For Docker/production (PostgreSQL):
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/noti
# For local development (PostgreSQL):
# DATABASE_URL=postgresql://postgres:postgres@localhost:5432/noti
```

**PostgreSQL Container** (for docker-compose):
```bash
POSTGRES_DB=noti
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

**Celery**:
```bash
CELERY_BROKER_URL=redis://redis:6379/0  # Docker
# CELERY_BROKER_URL=redis://localhost:6379/0  # Local
```

**APNs** (required for production):
```bash
APNS_KEY_ID=ABC123
APNS_TEAM_ID=DEF456
APNS_BUNDLE_ID=com.company.app
APNS_USE_SANDBOX=True      # False for production
```

### Settings Architecture (`core/settings.py`)

**Environment-based configuration**:
- Uses `python-dotenv` for `.env` file loading
- Uses `dj-database-url` for DATABASE_URL parsing
- PostgreSQL with Django 5.1+ native connection pooling (psycopg[pool])
- All sensitive values from environment variables
- Custom User model: `AUTH_USER_MODEL = "accounts.User"`

**Database Configuration**:
```python
DATABASES = {
    "default": dj_database_url.config(
        conn_health_checks=True,
    )
}

# Django 5.1+ native connection pooling
DATABASES["default"]["OPTIONS"] = {
    "pool": {
        "min_size": 2,  # Minimum connections
        "max_size": 10,  # Maximum connections
        "timeout": 30,  # Connection timeout
    }
}
```

**DRF Configuration**:
- JSON-only (no browsable API in prod)
- Pagination: 100 items per page
- drf-spectacular for OpenAPI docs

**Celery Configuration**:
- JSON serialization (security)
- Django DB result backend (tracking)
- Task tracking enabled
- 30-minute task timeout

## Docker Setup

### Services (`docker-compose.yml`)

1. **postgres** - PostgreSQL 18 Alpine
2. **redis** - Redis 7 Alpine with persistence
3. **web** - Django API (port 8000)
4. **celery_worker** - Background task processor
5. **celery_beat** - Scheduled tasks (cron-like)

**Key Features**:
- Health checks for postgres/redis
- `depends_on` with conditions (waits for DB/Redis)
- Volume mounts for hot-reload development
- Shared environment variables

### Dockerfile Strategy

**Base**: `python:3.14-slim`
**Package Manager**: `uv` (fast, modern)
**User**: Non-root `appuser` for security
**Workdir**: `/app/core` (where `manage.py` lives)

**Build optimization**:
- Copy `pyproject.toml` first (layer caching)
- Install deps before code copy
- `.dockerignore` excludes unnecessary files

## Development Workflow

### Just Commands (`justfile`)

**Local development** (without Docker):
```bash
just install        # Install dependencies
just infra          # Start just postgres + redis
just migrate        # Run migrations
just runserver      # Start Django
just worker         # Start Celery worker
just beat           # Start Celery beat
```

**Docker development**:
```bash
just build          # Build images
just up             # Start all services
just down           # Stop all services
just logs [service] # View logs
just docker-migrate # Run migrations in container
just bash           # Access container shell
```

**Code quality**:
```bash
just format         # Run pre-commit hooks
just lint           # Ruff linting
just fmt            # Ruff formatting
```

## Admin Interface

### Custom Admin

**User Admin** (`accounts/admin.py`):
- Email-based login (no username)
- Inline UserProfile editing
- Permission management
- Read-only timestamps

**DeviceOwner Admin** (`notifications/admin.py`):
- Shows device count per owner
- Searchable by external_id, name, email
- Filterable by active status
- Read-only timestamps

**Device Admin** (`notifications/admin.py`):
- Shows owner information
- Shortened token display (first 20 chars)
- Filterable by platform, active status
- Searchable by token and owner details
- Autocomplete for owner selection

**PushNotification Admin** (`notifications/admin.py`):
- **Colored status badges** (green=sent, red=failed, etc.)
- Filterable by status, priority, dates
- Searchable by title, body, token
- Grouped fieldsets (Target, Content, Delivery, Status)
- Read-only fields for tracking data

**Why custom admin**: Monitoring 200k notifications/day requires good UX

## Scaling Considerations

### Current Capacity
- **200k/day** = ~2.3 notifications/second average
- **100k/2 hours** = ~14 notifications/second peak
- **Single Celery worker** can handle this easily

### Horizontal Scaling
When needed (>1M/day):

1. **Celery workers**:
   ```bash
   docker-compose up -d --scale celery_worker=5
   ```

2. **Database**:
   - Add connection pooling (pgbouncer)
   - Read replicas for GET requests
   - Partition `push_notifications` table by date

3. **Redis**:
   - Redis Cluster for high availability
   - Separate queues for priorities

4. **Application servers**:
   - Multiple Django containers behind load balancer
   - Gunicorn with multiple workers per container

### Performance Optimization Tips

**Already implemented**:
- Database indexes on: `device_token`, `status`, `created_at`, `external_id`
- Celery task routing
- Django 5.1+ native connection pooling (psycopg[pool])
  - Min 2, Max 10 connections
  - Health checks enabled
  - 30-second timeout

**Future optimizations**:
- Bulk insert for bulk notifications (currently one-by-one)
- Redis caching for device lookups
- APNs connection pooling
- Monitoring with Flower/Prometheus

## Testing Strategy

### Current State
- Test framework: Django's built-in `TestCase`
- Test command: `uv run pytest` (or `just test`)

### What to Test

**Models**:
- Device upsert logic
- Notification state transitions
- Helper methods (`mark_as_sent`, etc.)

**API**:
- Device registration/update
- Single notification creation
- Bulk notification validation (max 1000)
- Filtering and pagination

**Tasks**:
- Mock APNs responses
- Retry logic
- Invalid token handling
- Error scenarios

**Example test structure**:
```python
# tests/test_notifications.py
class NotificationAPITest(TestCase):
    def test_create_notification_queues_task(self):
        # POST to /api/notifications/
        # Assert task was queued
        # Assert DB record created with status='queued'
```

## Common Development Tasks

### Add a new notification field

1. Update model:
   ```python
   # notifications/models.py
   class PushNotification(models.Model):
       new_field = models.CharField(max_length=100)
   ```

2. Update serializer:
   ```python
   # notifications/serializers.py
   class PushNotificationCreateSerializer:
       fields = [..., 'new_field']
   ```

3. Update APNs payload:
   ```python
   # notifications/tasks.py
   def build_apns_payload(notification):
       payload['aps']['new_field'] = notification.new_field
   ```

4. Migrate:
   ```bash
   just docker-makemigrations
   just docker-migrate
   ```

### Add a new Celery task

1. Define task:
   ```python
   # notifications/tasks.py
   @shared_task
   def cleanup_old_notifications():
       # Your logic
   ```

2. Add to beat schedule (optional):
   ```python
   # core/settings.py
   CELERY_BEAT_SCHEDULE = {
       'cleanup': {
           'task': 'notifications.tasks.cleanup_old_notifications',
           'schedule': crontab(hour=2, minute=0),
       },
   }
   ```

### Debug a stuck notification

1. Check admin: http://localhost:8000/admin/
2. Find notification by ID or status
3. Check error message field
4. View Celery logs:
   ```bash
   just logs celery_worker
   ```

## Production Deployment Checklist

### Pre-deployment
- [ ] Set `DEBUG=False`
- [ ] Generate new `SECRET_KEY`
- [ ] Set `ALLOWED_HOSTS`
- [ ] Set production `DATABASE_URL` (PostgreSQL)
- [ ] Create superuser account (`python manage.py createsuperuser`)
- [ ] Implement real APNs client in `tasks.py:150`
- [ ] Set `APNS_USE_SANDBOX=False`
- [ ] Configure SSL/TLS certificates

### Infrastructure
- [ ] Managed PostgreSQL with backups
- [ ] Managed Redis with persistence
- [ ] Load balancer for Django
- [ ] Process manager for Celery (supervisor/systemd)
- [ ] Monitoring (Sentry, Prometheus, Flower)
- [ ] Log aggregation (ELK, CloudWatch)

### Security
- [ ] Firewall rules (only load balancer → app)
- [ ] Database credentials in secrets manager
- [ ] APNs keys in secrets manager
- [ ] HTTPS only
- [ ] Rate limiting (django-ratelimit)
- [ ] API authentication (if needed)

## Known Limitations / TODOs

1. **APNs Integration**: Currently mocked (`tasks.py:150`)
   - Need to implement real HTTP/2 client
   - Add JWT token generation
   - Handle APNs connection pooling

2. **Bulk Operations**: One-by-one inserts
   - Could optimize with `bulk_create()`
   - Trade-off: lose individual validation

3. **Authentication**: No API auth currently
   - Add DRF Token Authentication if needed
   - Or API key middleware

4. **Rate Limiting**: Not implemented
   - Add django-ratelimit for public APIs
   - Prevent abuse of bulk endpoint

5. **Monitoring**: Basic logging only
   - Add APM (New Relic, DataDog)
   - Celery monitoring (Flower)
   - Alert on high failure rates

## Troubleshooting Guide

### "Celery worker not processing tasks"
1. Check Redis: `docker-compose logs redis`
2. Check worker is running: `just ps`
3. Restart worker: `just restart celery_worker`

### "Notifications stuck in queued"
1. Check Celery worker logs: `just logs celery_worker`
2. Verify APNs credentials in `.env`
3. Check for errors in admin interface

### "Database connection errors"
1. Check postgres health: `docker-compose ps postgres`
2. Verify DB credentials in docker-compose.yml
3. Check migrations: `just docker-migrate`

### "Build fails"
1. Clear Docker cache: `docker-compose build --no-cache`
2. Check Python version: Should be 3.14
3. Check uv.lock is committed

## Key Files Reference

| File | Purpose | Key Notes |
|------|---------|-----------|
| `core/settings.py` | Django config | DATABASE_URL, psycopg[pool], AUTH_USER_MODEL |
| `core/celery.py` | Celery app | Auto-discovers tasks |
| `accounts/models.py` | Auth models | Custom User (email login) + UserProfile |
| `accounts/admin.py` | User admin | Inline profile editing |
| `notifications/models.py` | Data models | DeviceOwner, Device, PushNotification, TimeStampedModel |
| `notifications/serializers.py` | DRF serializers | Separate for create/read |
| `notifications/views.py` | API endpoints | Bulk endpoint with 1000 limit |
| `notifications/tasks.py` | Celery tasks | APNs sending with retry logic |
| `notifications/admin.py` | Django admin | Colored badges, filtering, device owner tracking |
| `docker-compose.yml` | Docker services | 5 services, env_file, health checks |
| `Dockerfile` | Container image | Python 3.14, uv, non-root user |
| `.env.example` | Environment template | DATABASE_URL, connection pooling config |
| `justfile` | Commands | Both Docker and local dev |

## Philosophy

This project prioritizes:
1. **Reliability** over performance micro-optimizations
2. **Readability** over clever code
3. **Pragmatism** over architecture astronautics
4. **Battle-tested tools** over cutting-edge
5. **User's expertise** over theoretical "best practices"

The goal is a system that handles 200k notifications/day reliably, scales when needed, and is easy to maintain.
