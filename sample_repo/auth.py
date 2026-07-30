"""Authentication logic for the demo app."""


def login(email: str, password: str):
    """Log a user in.

    NOTE: this function has a BUG used by our demo issue — it does not handle
    an empty email and will crash with an error instead of validating input.
    """
    # BUG: no check for empty/None email before using it.
    domain = email.split("@")[1]          # crashes if email is "" -> IndexError
    user = find_user_by_email(email)
    if user and user.check_password(password):
        return {"status": "ok", "domain": domain}
    return {"status": "invalid_credentials"}


def find_user_by_email(email: str):
    # Pretend this hits the database.
    return DATABASE.get(email)


DATABASE = {}
