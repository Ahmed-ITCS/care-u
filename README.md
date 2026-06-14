# CARE-U — Multi-Tenant Hospital Management Platform

Production-ready **multi-tenant** Django 5+ hospital management platform. Multiple hospitals share one deployment with **PostgreSQL schema-based isolation** via [django-tenants](https://django-tenants.readthedocs.io/).

## Architecture

```
Public Schema (shared)          Tenant Schemas (per hospital)
├── Landing / Marketing         ├── gph_islamabad schema
├── Hospital Registration       │   ├── Patients, Appointments
├── Super Admin Panel           │   ├── Billing, Pharmacy, Lab
├── Subscription Plans          │   └── Staff, HR, Reports
└── PlatformUser (super admin)  └── gph_lahore schema (...)
```

**Access URLs:**
- Public site: `http://localhost:8000/`
- **Sign in (all hospitals)**: `http://localhost:8000/login/`
- Hospital dashboard: `http://localhost:8000/h/{subdomain}/` (auto-redirect after login)
- Production: `https://yourdomain.com/login/`

## Quick Start (Docker — Recommended)

```bash
cp .env.example .env
cd docker
docker compose up --build
```

Then visit:
- **Landing page**: http://localhost:8000/
- **Register hospital**: http://localhost:8000/register/
- **Platform admin**: http://localhost:8000/platform/login/ (`superadmin` / `superadmin123`)
- **Hospital dashboard**: http://localhost:8000/h/{subdomain}/

## Local Development

**Default: SQLite** (`db.sqlite3` in the project root — no PostgreSQL install required).

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements/dev.txt

cp .env.example .env

cd frontend && npm install && npm run build:css && cd ..

python manage.py migrate
python manage.py setup_public_tenant
python manage.py seed_plans
python manage.py create_platform_admin
python manage.py seed_demo --migrate

python manage.py runserver
```

Access demo hospital: http://localhost:8000/h/gph-islamabad/

### PostgreSQL (production / full schema isolation)

For Render or local PostgreSQL with per-hospital schema isolation, set in `.env`:

```
DB_ENGINE=postgres
DATABASE_URL=postgres://user:pass@localhost:5432/gph_erp
```

Then use `migrate_schemas` instead of `migrate` (see Docker setup below).

## Management Commands

| Command | Description |
|---------|-------------|
| `migrate_schemas --shared` | Migrate public schema |
| `migrate_schemas --tenant` | Migrate all tenant schemas |
| `create_hospital` | Create hospital + schema + admin |
| `setup_public_tenant` | Create public schema tenant (required for `/`) |
| `fix_tenant_domains` | Repair subfolder/subdomain Domain records |
| `create_platform_admin` | Create super admin (public schema) |
| `create_tenant_admin` | Create hospital admin in existing tenant |

### Do NOT use `createsuperuser`

`users.User` lives in **tenant schemas only** (not public). Running `createsuperuser` will fail with `relation "users_user" does not exist`.

Use the commands above instead:

```bash
# Platform super admin → /platform/login/
python manage.py create_platform_admin --username superadmin --password yourpass

# Hospital admin → /h/{subdomain}/users/login/
python manage.py create_tenant_admin \
  --subdomain gph-islamabad \
  --username admin \
  --email admin@hospital.com \
  --password yourpass \
  --name "Hospital Admin"
```
| `seed_plans` | Seed subscription plans |

## Demo Credentials

### Platform Super Admin (public schema)
| Username | Password |
|----------|----------|
| superadmin | superadmin123 |

### Hospital Admin (tenant schema — after create_hospital)
| URL | Username | Password |
|-----|----------|----------|
| /h/gph-islamabad/ | admin@gph.com.pk prefix | admin123 |

## Multi-Tenancy Details

### Data Isolation
- Each hospital gets a dedicated **PostgreSQL schema**
- All ERP queries run within the tenant schema automatically
- Cross-tenant data access is prevented at the database level

### User Models
- **`PlatformUser`** — Super Admin in public schema (manages all hospitals)
- **`User`** — Hospital staff/patients in tenant schema (per hospital)

### Subscription Plans
- **Free Trial** (14 days) → **Basic** → **Premium** → **Enterprise**
- Suspended/expired tenants are blocked by `TenantAccessMiddleware`

### Customization per Hospital
- Logo, primary/accent colors
- Tax rates, receipt header/footer
- Configured via onboarding wizard or Settings page

## API Access

**Unified login** (no tenant prefix):
```
POST http://localhost:8000/api/v1/auth/login/
{ "username": "admin", "password": "admin123" }
```

Response includes `tenant`, `api_base_url`, and JWT tokens. Use `api_base_url` for all other API calls:
```
http://localhost:8000/h/gph-islamabad/api/v1/
http://localhost:8000/h/gph-islamabad/api/docs/
```

## Production Deployment

1. Set `DJANGO_SETTINGS_MODULE=config.settings.production`
2. Configure PostgreSQL, Redis, S3
3. Set `BASE_DOMAIN=yourdomain.com`
4. Switch to `TenantMainMiddleware` for subdomain routing (set `TENANT_USE_SUBFOLDER=false`)
5. Use gunicorn + daphne behind nginx with wildcard SSL (`*.yourdomain.com`)

## Testing

```bash
# Requires PostgreSQL test database
pytest tests/ --cov=apps
```

## License

Proprietary — CARE-U Platform
