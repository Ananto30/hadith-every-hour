"""Keep a Facebook Page token fresh without manual intervention.

A Page token cannot be exchanged directly. Instead we store a long-lived
user token and derive the Page token from it. Shortly before the user token
expires, a scheduled workflow exchanges it for a new one and derives a new
Page token.

The state is encrypted with Fernet and committed to the repository. The key
lives in the TOKEN_ENCRYPTION_KEY GitHub secret, so the public repository only
ever contains ciphertext. Run this module with ``python -m src.fb_token``.
"""

import json
import os
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

from src.utils import decrypt, encrypt, ensure_env_var, get_optional_env_var

GRAPH_API_URL = "https://graph.facebook.com"
STATE_FILE = Path("resources/fb_token.enc")
REFRESH_WINDOW_SECONDS = 14 * 24 * 60 * 60
NEVER_EXPIRES = 0


class FacebookTokenError(RuntimeError):
    """Raised when a token cannot be refreshed automatically."""


@dataclass
class TokenState:
    page_token: str
    page_expires_at: int = NEVER_EXPIRES
    user_token: str | None = None
    user_expires_at: int = NEVER_EXPIRES
    user_token_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_token": self.page_token,
            "page_expires_at": self.page_expires_at,
            "user_token": self.user_token,
            "user_expires_at": self.user_expires_at,
            "user_token_type": self.user_token_type,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TokenState":
        page_token = data.get("page_token")
        if not isinstance(page_token, str) or not page_token:
            raise ValueError("Missing page token")

        user_token = data.get("user_token")
        if user_token is not None and not isinstance(user_token, str):
            raise ValueError("Invalid user token")

        user_token_type = data.get("user_token_type")
        if user_token_type is not None and not isinstance(
            user_token_type, str
        ):
            raise ValueError("Invalid user token type")

        return cls(
            page_token=page_token,
            page_expires_at=_as_int(data.get("page_expires_at")),
            user_token=user_token or None,
            user_expires_at=_as_int(data.get("user_expires_at")),
            user_token_type=user_token_type,
        )


def _as_int(value: Any, default: int = NEVER_EXPIRES) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _format_expiry(expires_at: int) -> str:
    if expires_at == NEVER_EXPIRES:
        return "never"
    return datetime.fromtimestamp(expires_at, tz=UTC).isoformat()


def _graph_request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    token: str | None = None,
) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    try:
        response = requests.request(
            method,
            f"{GRAPH_API_URL}{path}",
            params=params,
            data=data,
            headers=headers,
            timeout=15,
        )
    except requests.RequestException as exc:
        # Do not include the URL in the error. OAuth calls put the app
        # secret and token in query parameters.
        raise FacebookTokenError(
            f"Facebook request failed ({type(exc).__name__})."
        ) from None

    try:
        payload = response.json()
    except ValueError:
        raise FacebookTokenError(
            f"Facebook returned HTTP {response.status_code} without JSON."
        ) from None

    if not isinstance(payload, dict):
        raise FacebookTokenError(
            f"Facebook returned HTTP {response.status_code} with an "
            "unexpected payload."
        )

    if response.status_code >= 400 or "error" in payload:
        error = payload.get("error")
        if not isinstance(error, dict):
            error = {}
        code = error.get("code", response.status_code)
        message = error.get("message", "Unknown Graph API error")
        raise FacebookTokenError(f"Facebook API error {code}: {message}")

    return payload


def debug_token(token: str) -> dict[str, Any]:
    app_id = ensure_env_var("FB_APP_ID")
    app_secret = ensure_env_var("FB_APP_SECRET")
    payload = _graph_request(
        "GET",
        "/debug_token",
        params={"input_token": token},
        token=f"{app_id}|{app_secret}",
    )
    info = payload.get("data")
    if not isinstance(info, dict):
        raise FacebookTokenError("Facebook did not return token details.")
    return info


def _require_valid(info: dict[str, Any], label: str) -> None:
    if not info.get("is_valid"):
        raise FacebookTokenError(f"{label} is invalid or has expired.")


def _require_page_scopes(info: dict[str, Any], label: str) -> None:
    scopes = info.get("scopes")
    if not isinstance(scopes, list) or not scopes:
        return
    if "pages_manage_posts" not in scopes:
        raise FacebookTokenError(
            f"{label} is missing the pages_manage_posts permission."
        )


def _expiry_from_info(info: dict[str, Any], fallback: int) -> int:
    return _as_int(info.get("expires_at"), fallback)


def exchange_user_token(
    token: str, token_type: str | None = None
) -> tuple[str, int]:
    """Exchange a user or system-user token for a fresh long-lived one."""
    app_id = ensure_env_var("FB_APP_ID")
    app_secret = ensure_env_var("FB_APP_SECRET")
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": token,
    }
    if token_type == "SYSTEM_USER":
        params["set_token_expires_in_60_days"] = "true"

    payload = _graph_request("GET", "/oauth/access_token", params=params)
    new_token = payload.get("access_token")
    if not isinstance(new_token, str) or not new_token:
        raise FacebookTokenError("Facebook did not return a refreshed token.")

    expires_in = payload.get("expires_in")
    fallback_expiry = NEVER_EXPIRES
    if expires_in is not None:
        try:
            fallback_expiry = int(time.time()) + int(expires_in)
        except (TypeError, ValueError):
            fallback_expiry = NEVER_EXPIRES

    info = debug_token(new_token)
    _require_valid(info, "Refreshed user token")
    return new_token, _expiry_from_info(info, fallback_expiry)


def derive_page_token(user_token: str) -> tuple[str, int]:
    """Derive the Page token that belongs to the user token."""
    page_id = ensure_env_var("FB_PAGE_ID")
    payload = _graph_request(
        "GET",
        f"/{page_id}",
        params={"fields": "access_token"},
        token=user_token,
    )
    page_token = payload.get("access_token")
    if not isinstance(page_token, str) or not page_token:
        raise FacebookTokenError(
            "Could not derive a Page token. Make sure the user has "
            "pages_show_list and pages_manage_posts permissions and a role "
            "on the Page."
        )

    info = debug_token(page_token)
    _require_valid(info, "Derived Page token")
    return page_token, _expiry_from_info(info, NEVER_EXPIRES)


def load_state() -> TokenState | None:
    if not STATE_FILE.exists():
        return None

    try:
        encrypted = STATE_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        raise FacebookTokenError(f"Could not read {STATE_FILE}.") from None

    if not encrypted:
        return None

    key = ensure_env_var("TOKEN_ENCRYPTION_KEY")
    try:
        raw = decrypt(key, encrypted)
    except Exception:
        raise FacebookTokenError(
            f"Could not decrypt {STATE_FILE}. If TOKEN_ENCRYPTION_KEY was "
            "changed, delete the file and re-bootstrap with FB_USER_TOKEN."
        ) from None

    try:
        data = json.loads(raw)
    except ValueError:
        raise FacebookTokenError(
            "Facebook token state is malformed."
        ) from None

    if not isinstance(data, dict):
        raise FacebookTokenError("Facebook token state is malformed.")

    try:
        return TokenState.from_dict(data)
    except ValueError:
        raise FacebookTokenError(
            "Facebook token state is malformed."
        ) from None


def save_state(state: TokenState) -> None:
    key = ensure_env_var("TOKEN_ENCRYPTION_KEY")
    payload = encrypt(key, json.dumps(state.to_dict(), separators=(",", ":")))
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp_file = STATE_FILE.with_name(f"{STATE_FILE.name}.tmp")
    temp_file.write_text(payload, encoding="utf-8")
    os.chmod(temp_file, 0o600)
    os.replace(temp_file, STATE_FILE)


def bootstrap_state() -> TokenState:
    """Create the encrypted state from the one-time GitHub secrets."""
    user_token = get_optional_env_var("FB_USER_TOKEN")
    page_token = get_optional_env_var("FB_PAGE_TOKEN")

    if user_token:
        info = debug_token(user_token)
        _require_valid(info, "FB_USER_TOKEN")
        token_type = str(info.get("type") or "USER")
        expires_at = _expiry_from_info(info, NEVER_EXPIRES)

        if token_type == "PAGE":
            if expires_at != NEVER_EXPIRES:
                raise FacebookTokenError(
                    "FB_USER_TOKEN is a finite Page token, which cannot be "
                    "exchanged. Use a long-lived user token instead."
                )
            return TokenState(
                page_token=user_token,
                page_expires_at=NEVER_EXPIRES,
            )

        if token_type not in ("USER", "SYSTEM_USER"):
            raise FacebookTokenError(
                f"Unsupported token type in FB_USER_TOKEN: {token_type}."
            )

        _require_page_scopes(info, "FB_USER_TOKEN")

        # Exchange short-lived tokens immediately. Leave a healthy long-lived
        # token alone: Meta only allows re-exchanging a long-lived token after
        # it is 24 hours old, so exchanging a freshly created one can fail.
        if _expires_within(expires_at, int(time.time())):
            user_token, expires_at = exchange_user_token(
                user_token, token_type
            )
            info = debug_token(user_token)
            token_type = str(info.get("type") or token_type)

        page_token, page_expires_at = derive_page_token(user_token)
        return TokenState(
            page_token=page_token,
            page_expires_at=page_expires_at,
            user_token=user_token,
            user_expires_at=expires_at,
            user_token_type=token_type,
        )

    if page_token:
        info = debug_token(page_token)
        _require_valid(info, "FB_PAGE_TOKEN")
        expires_at = _expiry_from_info(info, NEVER_EXPIRES)
        if expires_at != NEVER_EXPIRES:
            raise FacebookTokenError(
                "FB_PAGE_TOKEN expires and Page tokens cannot be exchanged. "
                "Add a long-lived FB_USER_TOKEN (with pages_show_list and "
                "pages_manage_posts) to enable automatic refresh."
            )
        return TokenState(
            page_token=page_token,
            page_expires_at=NEVER_EXPIRES,
        )

    raise FacebookTokenError(
        "No Facebook token found. Add FB_USER_TOKEN as a repository secret "
        "to bootstrap automatic refresh."
    )


def _expires_within(expires_at: int, now: int) -> bool:
    return (
        expires_at != NEVER_EXPIRES
        and expires_at - now <= REFRESH_WINDOW_SECONDS
    )


def refresh_state(state: TokenState) -> TokenState:
    """Refresh tokens that are close to expiry and persist the result."""
    if state.user_token is None and get_optional_env_var("FB_USER_TOKEN"):
        # The initial state was page-only. Now that a user token is
        # available, upgrade it so future refreshes can re-derive the Page
        # token.
        print("Found FB_USER_TOKEN; upgrading to a refreshable token state.")
        upgraded_state = bootstrap_state()
        save_state(upgraded_state)
        return upgraded_state

    now = int(time.time())

    page_info = debug_token(state.page_token)
    page_valid = bool(page_info.get("is_valid"))
    page_expires_at = _expiry_from_info(page_info, state.page_expires_at)
    page_needs_refresh = not page_valid or _expires_within(
        page_expires_at, now
    )

    user_info = debug_token(state.user_token) if state.user_token else None
    user_valid = bool(user_info and user_info.get("is_valid"))
    user_expires_at = (
        _expiry_from_info(user_info, state.user_expires_at)
        if user_info
        else state.user_expires_at
    )
    user_type = (
        str(user_info.get("type") or state.user_token_type or "USER")
        if user_info
        else state.user_token_type
    )
    user_needs_refresh = user_valid and _expires_within(user_expires_at, now)

    if not page_needs_refresh and not user_needs_refresh:
        print(
            "Facebook tokens are healthy; no refresh needed "
            f"(Page: {_format_expiry(page_expires_at)}, "
            f"user: {_format_expiry(user_expires_at)})."
        )
        if state.user_token and not user_valid:
            print(
                "::warning::The stored user token is no longer valid. The "
                "Page token still works; re-bootstrap with a new "
                "FB_USER_TOKEN to restore automatic recovery."
            )
        return state

    if page_needs_refresh and not user_valid:
        raise FacebookTokenError(
            "The Page token needs refreshing, but the stored user token is "
            "missing or invalid. Re-bootstrap with a new FB_USER_TOKEN and "
            "run this workflow manually."
        )

    new_user_token = state.user_token
    new_user_expires_at = user_expires_at
    new_user_type = user_type

    if user_needs_refresh:
        if not state.user_token:
            raise FacebookTokenError("No user token available to refresh.")
        try:
            new_user_token, new_user_expires_at = exchange_user_token(
                state.user_token, user_type
            )
        except FacebookTokenError as exc:
            if (
                not page_needs_refresh
                and page_valid
                and page_expires_at == NEVER_EXPIRES
            ):
                print(
                    "::warning::Could not refresh the user token "
                    f"({exc}). The Page token does not expire, so posting "
                    "can continue; re-bootstrap with a new FB_USER_TOKEN "
                    "to restore automatic recovery."
                )
                return state
            raise
        new_user_info = debug_token(new_user_token)
        new_user_type = str(new_user_info.get("type") or user_type or "USER")
        print(
            "Refreshed user token; expires "
            f"{_format_expiry(new_user_expires_at)}."
        )

    new_page_token = state.page_token
    new_page_expires_at = page_expires_at

    if page_needs_refresh:
        if not new_user_token:
            raise FacebookTokenError(
                "No user token available to derive a Page token."
            )
        new_page_token, new_page_expires_at = derive_page_token(new_user_token)
        print(
            "Derived a new Page token; expires "
            f"{_format_expiry(new_page_expires_at)}."
        )

    refreshed_state = TokenState(
        page_token=new_page_token,
        page_expires_at=new_page_expires_at,
        user_token=new_user_token,
        user_expires_at=new_user_expires_at,
        user_token_type=new_user_type,
    )
    save_state(refreshed_state)
    return refreshed_state


def main() -> None:
    try:
        force_bootstrap = os.getenv("FB_FORCE_BOOTSTRAP") == "true"
        if force_bootstrap and not get_optional_env_var("FB_USER_TOKEN"):
            raise FacebookTokenError(
                "Force bootstrap requires FB_USER_TOKEN. Set it before "
                "replacing the stored token state."
            )
        state = None if force_bootstrap else load_state()

        if state is None:
            if force_bootstrap:
                print("Force bootstrap requested; replacing stored state.")
            else:
                print(
                    "No encrypted token state found; bootstrapping from "
                    "secrets."
                )
            state = bootstrap_state()
            save_state(state)
            print(
                "Created the encrypted token state; Page token expires "
                f"{_format_expiry(state.page_expires_at)}."
            )
        else:
            refresh_state(state)
    except (FacebookTokenError, ValueError) as exc:
        print(f"::error::{exc}")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
