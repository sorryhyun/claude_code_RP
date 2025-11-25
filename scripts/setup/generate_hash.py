#!/usr/bin/env python3
"""
Utility script to generate bcrypt password hashes for the API_KEY_HASH.

Usage:
    python generate_hash.py

This will prompt you for a password and output a bcrypt hash that you can
add to your .env file as API_KEY_HASH.
"""

import getpass

import bcrypt


def generate_hash():
    """Generate a bcrypt hash from user input."""
    print("=" * 60)
    print("Claude Code Role Play Password Hash Generator")
    print("=" * 60)
    print()
    print("This script will generate a bcrypt hash for your password.")
    print("Add the generated hash to your .env file as API_KEY_HASH.")
    print()

    # Get password from user
    password = getpass.getpass("Enter your desired password: ")
    password_confirm = getpass.getpass("Confirm password: ")

    if password != password_confirm:
        print("\n❌ Passwords do not match. Please try again.")
        return

    if len(password) < 8:
        print("\n⚠️  Warning: Password is less than 8 characters.")
        print("   Consider using a longer password for better security.")
        proceed = input("Continue anyway? (y/N): ")
        if proceed.lower() != "y":
            print("Aborted.")
            return

    # Generate hash
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(password.encode("utf-8"), salt)
    hash_str = password_hash.decode("utf-8")

    # Display result
    print("\n" + "=" * 60)
    print("✅ Hash generated successfully!")
    print("=" * 60)
    print()
    print("Add this line to your .env file:")
    print()
    print(f"API_KEY_HASH={hash_str}")
    print()
    print("=" * 60)
    print()
    print("📝 Notes:")
    print("  - Keep this hash secret and don't commit it to git")
    print("  - You can remove the old API_KEY line from .env")
    print("  - Users will login with the original password, not the hash")
    print("  - Restart your backend server after updating .env")
    print()


if __name__ == "__main__":
    try:
        generate_hash()
    except KeyboardInterrupt:
        print("\n\nAborted.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
