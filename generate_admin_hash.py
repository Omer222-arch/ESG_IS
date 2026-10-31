import getpass
import secrets
import hashlib
import sys

password = getpass.getpass("New admin password: ")
confirm = getpass.getpass("Confirm password: ")

if len(password) < 12:
    sys.exit("Use at least 12 characters. No changes made.")

if password != confirm:
    sys.exit("Passwords do not match. No changes made.")

salt = secrets.token_bytes(16)
iterations = 600000
digest = hashlib.pbkdf2_hmac(
    "sha256", password.encode("utf-8"), salt, iterations
)

print(
    "ADMIN_PASSWORD_HASH=pbkdf2_sha256$"
    + str(iterations) + "$" + salt.hex() + "$" + digest.hex()
)
