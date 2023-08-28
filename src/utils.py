import os

from cryptography.fernet import Fernet


def ensure_env_var(var_name: str) -> str:
    """
    Ensure that an environment variable is set.

    Args:
        var_name: The name of the environment variable.

    Returns:
        The value of the environment variable.

    Raises:
        ValueError: If the environment variable is not set.
    """
    var = os.getenv(var_name)
    if var is None:
        raise ValueError(f"Environment variable {var_name} is not set.")
    return var


def encrypt(key: str, value: str) -> str:
    fernet = Fernet(bytes(key, "utf-8"))
    return fernet.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt(key: str, value: str) -> str:
    fernet = Fernet(bytes(key, "utf-8"))
    return fernet.decrypt(value.encode("utf-8")).decode("utf-8")
