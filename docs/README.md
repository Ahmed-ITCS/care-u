# CARE-U Documentation (LaTeX)

Two separate documents:

| File | Audience | Contents |
|------|----------|----------|
| `technical-documentation.tex` | Developers, DevOps | Architecture, tenancy, API, deployment, security |
| `user-documentation.tex` | Hospital staff, admins | Registration, login, modules, roles, CSV import |

## Compile to PDF

Requires a LaTeX distribution (TeX Live, MacTeX, or MiKTeX).

```bash
cd docs

# Technical doc
pdflatex technical-documentation.tex
pdflatex technical-documentation.tex   # second pass for TOC

# User guide
pdflatex user-documentation.tex
pdflatex user-documentation.tex
```

Or with `latexmk`:

```bash
latexmk -pdf technical-documentation.tex
latexmk -pdf user-documentation.tex
```

Output: `technical-documentation.pdf` and `user-documentation.pdf`.
