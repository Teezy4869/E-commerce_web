"""Provision five local demo staff accounts with unique generated passwords."""

import argparse
import secrets
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from application.admin_service import AdminService
from application.commerce_service import CommerceService
from data.admin_repository import AdminRepository
from data.catalog_repository import CatalogRepository


ACCOUNTS = (
    ("admin@cogu.demo", "COGU Administrator", "administrator"),
    ("sales@cogu.demo", "COGU Sales", "sales"),
    ("warehouse@cogu.demo", "COGU Warehouse", "warehouse"),
    ("support@cogu.demo", "COGU Support", "support"),
    ("manager@cogu.demo", "COGU Manager", "manager"),
)


def main():
    parser = argparse.ArgumentParser(description="Provision local COGU staff demo accounts")
    parser.add_argument("--db", help="SQLite path; defaults to COGU_CATALOG_DB or the project catalogue")
    parser.add_argument("--reset", action="store_true", help="Generate new passwords for existing demo accounts and revoke their sessions")
    args = parser.parse_args()
    catalog = CatalogRepository(db_path=args.db)
    repository = AdminRepository(catalog.db_path)
    service = AdminService(repository, ROOT / "images")
    print(f"Demo database: {catalog.db_path}")
    print("Save these one-time passwords locally. This script does not store plaintext passwords.\n")
    for email, name, role in ACCOUNTS:
        existing = repository.find_staff_by_email(email)
        if existing and not args.reset:
            print(f"{role:14} {email:24} already exists; password unchanged (use --reset to rotate)")
            continue
        password = secrets.token_urlsafe(18)
        if existing:
            salt = secrets.token_hex(16)
            repository.reset_staff_password(email, CommerceService._hash_password(password, salt), salt)
        else:
            service.seed_staff(email, name, role, password)
        print(f"{role:14} {email:24} {password}")
    print("\nOpen http://127.0.0.1:8080/admin after starting run_ui.py.")


if __name__ == "__main__":
    main()
