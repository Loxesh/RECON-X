
"""Create the initial RECON X development organisation and admin user."""

from getpass import getpass

from app.core.database import create_mongo_client, ping_mongodb
from app.core.security import hash_password
from app.core.permissions import Role
from app.core.config import settings
from app.models.organization import OrganizationDocument
from app.models.user import UserDocument
from app.repositories.organization import OrganizationRepository
from app.repositories.tenant_collections import UserRepository


def main():
    client = create_mongo_client()

    try:
        if not ping_mongodb(client):
            raise RuntimeError("MongoDB connection failed.")

        database = client[settings.mongodb_database]

        print("\nRECON X - Development Account Setup\n")

        organization_name = input(
            "Organisation name [RECON X Demo]: "
        ).strip() or "RECON X Demo"

        organization_slug = input(
            "Organisation slug [recon-x-demo]: "
        ).strip().lower() or "recon-x-demo"

        email = input("Administrator email: ").strip().lower()

        if not email:
            raise ValueError("Email cannot be empty.")

        password = getpass("Create administrator password: ")
        confirm_password = getpass("Confirm password: ")

        if not password:
            raise ValueError("Password cannot be empty.")

        if password != confirm_password:
            raise ValueError("Passwords do not match.")

        organization_repository = OrganizationRepository(database)

        organization = organization_repository.get_by_slug(
            organization_slug
        )

        if organization:
            if organization.get("status") != "ACTIVE":
                raise RuntimeError(
                    "The existing organisation is not active."
                )

            print("\nExisting organisation found. Reusing it.")

        else:
            organization = organization_repository.create(
                OrganizationDocument(
                    name=organization_name,
                    slug=organization_slug,
                )
            )

            print("\nOrganisation created successfully.")

        organization_id = str(organization["_id"])

        existing_user = database["users"].find_one(
            {
                "org_id": organization_id,
                "email": email,
            }
        )

        if existing_user:
            raise RuntimeError(
                "An account with this email already exists "
                "in this organisation. No changes made to that account."
            )

        user_document = UserDocument(
            org_id=organization_id,
            email=email,
            password_hash=hash_password(password),
            roles=[Role.ORG_ADMIN.value],
        )

        user_repository = UserRepository(
            database,
            organization_id,
        )

        created_user = user_repository.create(user_document)

        print("\nDevelopment account created successfully!")
        print("----------------------------------------")
        print("Organisation:", organization["name"])
        print("Organisation slug:", organization["slug"])
        print("Organisation ID:", organization_id)
        print("Administrator email:", email)
        print("Role: org_admin")
        print("User ID:", str(created_user["_id"]))
        print("----------------------------------------")
        print("Password: securely hashed using Argon2.")
        print("You can now log in through the RECON X API.")

    finally:
        client.close()


if __name__ == "__main__":
    main()
