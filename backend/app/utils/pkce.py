"""
PKCE (Proof Key for Code Exchange) helpers for the Spotify OAuth 2.0 flow.

Why PKCE?
---------
With PKCE, the client generates a random secret (code_verifier), sends only
a hash of it (code_challenge) when redirecting to Spotify, and then proves
ownership of the secret when exchanging the auth code for tokens.
This prevents auth code interception attacks and means we don't need to
expose the client_secret to the browser.

Spotify PKCE spec: https://developer.spotify.com/documentation/web-api/tutorials/code-pkce-flow
"""

import base64
import hashlib
import secrets


def generate_code_verifier() -> str:
    """
    Generate a cryptographically random PKCE code verifier.

    Produces a 43-character URL-safe string (no padding).
    Spec: 43–128 unreserved ASCII characters [A-Z a-z 0-9 -._~].
    """
    return secrets.token_urlsafe(32)  # 32 bytes → 43 base64url chars


def generate_code_challenge(verifier: str) -> str:
    """
    Derive the PKCE code challenge from the verifier using SHA-256.

    Formula: BASE64URL(SHA256(ASCII(code_verifier)))
    The trailing '=' padding is stripped as required by the spec.
    """
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def generate_state() -> str:
    """
    Generate a random CSRF state parameter.

    Stored in the session before redirecting to Spotify and validated
    when Spotify redirects back to our callback endpoint.
    """
    return secrets.token_urlsafe(16)
