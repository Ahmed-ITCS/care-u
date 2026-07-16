# Landing page screenshots

Drop your product screenshots here. The landing page (`templates/tenants/landing.html`)
references these exact filenames. Until a file exists, a styled placeholder is shown
in its place automatically (no broken images).

| Filename          | Where it appears                          | Suggested size      |
|-------------------|-------------------------------------------|---------------------|
| `dashboard.png`   | Main hero / product preview (browser frame) and gallery | 2400×1500 (16:10)   |
| `opd-queue.png`   | Screenshot gallery (click to enlarge)     | 2400×1500 (16:10)   |
| `ipd.png`         | Screenshot gallery (click to enlarge)     | 2400×1500 (16:10)   |
| `billing.png`     | Screenshot gallery (click to enlarge)     | 2400×1500 (16:10)   |
| `pharmacy.png`    | Screenshot gallery (click to enlarge)     | 2400×1500 (16:10)   |
| `laboratory.png`  | Screenshot gallery (click to enlarge)     | 2400×1500 (16:10)   |

After adding files in production, run:

    python manage.py collectstatic --noinput

In local dev (DEBUG=True) they are served directly — no collectstatic needed.
