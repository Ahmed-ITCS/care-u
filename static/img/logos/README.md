# Customer / hospital logos

Drop hospital logos here for the "Trusted by" strip on the landing page.
The template references `hospital-1.png` … `hospital-5.png`. Any that are missing
fall back to a neutral placeholder chip automatically.

- Format: PNG or SVG, transparent background
- Recommended: monochrome / grayscale, ~200×64px, trimmed padding

After adding files in production, run `python manage.py collectstatic --noinput`.
