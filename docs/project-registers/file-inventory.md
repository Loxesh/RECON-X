# RECON X - File Inventory

**Last Updated:** 12 November 2026

## Root Structure

| Path | Purpose |
|---|---|
| README.md | Project overview and setup information |
| .gitignore | Excludes secrets, environments and generated files |
| backend/ | FastAPI backend |
| frontend/ | React + Vite frontend |
| docker/ | Container configuration |
| scripts/ | Project utility scripts |
| sample_data/ | Sample input data |
| docs/ | Project documentation and registers |
| .github/workflows/ | CI workflow directory |

## Backend Files

| File | Purpose |
|---|---|
| backend/pyproject.toml | Python project configuration and dependencies |
| backend/app/__init__.py | Backend application package |
| backend/app/main.py | FastAPI application and health endpoint |
| backend/tests/test_health.py | Health endpoint test |

## Frontend Files

| File | Purpose |
|---|---|
| frontend/package.json | Frontend dependencies and scripts |
| frontend/package-lock.json | Locked frontend dependency versions |
| frontend/index.html | Application HTML entry point |
| frontend/vite.config.js | Vite, React and Tailwind plugin configuration |
| frontend/eslint.config.js | ESLint configuration |
| frontend/src/main.jsx | React entry point |
| frontend/src/App.jsx | Initial RECON X dashboard shell |
| frontend/src/App.css | Reusable component styles |
| frontend/src/index.css | Global styles and design tokens |
| frontend/public/favicon.svg | Vite starter favicon asset |
| frontend/public/icons.svg | Vite starter icon asset |
| frontend/src/assets/ | Initial Vite starter assets |

## Project Registers

| File | Purpose |
|---|---|
| docs/project-registers/api-contract-register.md | Implemented and planned API endpoints |
| docs/project-registers/environment-variables-register.md | Environment variable tracking |
| docs/project-registers/file-inventory.md | Project file inventory |
| docs/project-registers/chapter-completion-record.md | Workbook chapter progress |

## Notes

- Python virtual environments, node_modules and frontend dist output are excluded from Git.
- The frontend uses JavaScript and JSX, not TypeScript.
- Additional modules will be recorded as implementation progresses.