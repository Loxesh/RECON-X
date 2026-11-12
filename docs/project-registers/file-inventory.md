
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
| backend/.env.example | Safe local environment configuration template |
| backend/pyproject.toml | Python project configuration and dependencies |
| backend/app/__init__.py | Backend application package |
| backend/app/main.py | FastAPI application and health endpoint |
| backend/app/core/__init__.py | Core configuration package |
| backend/app/core/config.py | Central Pydantic Settings configuration loader |
| backend/tests/test_health.py | Health endpoint test |

## Local Development Files

| File | Purpose | Git Status |
|---|---|---|
| backend/.env | Local application and MongoDB Atlas configuration | Ignored |
| backend/.env.example | Shareable configuration template | Trackable |

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
| frontend/public/favicon.svg | Favicon asset |
| frontend/public/icons.svg | Icon asset |
| frontend/src/assets/ | Frontend assets |

## Operations Documentation

| File | Purpose |
|---|---|
| docs/operations/mongodb-atlas.md | MongoDB Atlas development setup and connection verification |

## Project Registers

| File | Purpose |
|---|---|
| docs/project-registers/api-contract-register.md | Implemented and planned API endpoints |
| docs/project-registers/environment-variables-register.md | Environment variable tracking |
| docs/project-registers/file-inventory.md | Project file inventory |
| docs/project-registers/chapter-completion-record.md | Workbook chapter progress |

## Notes

- Python virtual environments, node_modules and frontend dist output are excluded from Git.
- Local `.env` files must never be committed.
- `.env.example` must contain safe placeholders only.
- The frontend uses JavaScript and JSX, not TypeScript.
- MongoDB Atlas is used as the development database.
- PyMongo is the approved synchronous MongoDB driver.
- Database lifecycle management, collections, indexes and tenant-scoped repositories will be implemented in subsequent chapters.
- Additional modules will be recorded as implementation progresses.
