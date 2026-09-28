"""Configuration and access checks for the single-owner hosted deployment."""
import base64
import binascii
import hmac
import os
from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Hosting:
    hosted: bool
    username: str
    password: str
    hosts: list[str]
    origins: set[str]
    ephemeral: bool

    @classmethod
    def from_environment(cls):
        hosted = os.getenv('EVAL_HOSTED') == '1' or os.getenv('RENDER') == 'true'
        username = os.getenv('EVAL_USERNAME', 'owner')
        password = os.getenv('EVAL_PASSWORD', '')
        hosts = ['localhost', '127.0.0.1']
        origins = {'http://localhost:8000', 'http://127.0.0.1:8000',
                   'http://localhost:5173', 'http://127.0.0.1:5173'}
        if not hosted:
            hosts.append('testserver')
        if hosted and (len(password) < 16 or not username or ':' in username):
            raise ValueError('Hosted mode requires EVAL_PASSWORD with at least 16 characters and a valid EVAL_USERNAME')
        external_host = os.getenv('RENDER_EXTERNAL_HOSTNAME', '').strip()
        if external_host:
            if any(c in external_host for c in '/:*@?#'):
                raise ValueError('RENDER_EXTERNAL_HOSTNAME must be a hostname')
            hosts.append(external_host)
            origins.add(f'https://{external_host}')
        public_url = os.getenv('EVAL_PUBLIC_URL', '').rstrip('/')
        if public_url:
            parsed = urlsplit(public_url)
            if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
                raise ValueError('EVAL_PUBLIC_URL must be an HTTPS origin, such as https://eval.example.com')
            hosts.append(parsed.hostname)
            origins.add(public_url)
        return cls(hosted, username, password, hosts, origins,
                   os.getenv('EVAL_STORAGE_EPHEMERAL') == '1')

    def authenticated(self, authorization):
        try:
            scheme, encoded = (authorization or '').split(' ', 1)
            if scheme.lower() != 'basic':
                return False
            user, password = base64.b64decode(encoded, validate=True).decode('utf-8').split(':', 1)
        except (ValueError, UnicodeDecodeError, binascii.Error):
            return False
        user_ok = hmac.compare_digest(user.encode(), self.username.encode())
        password_ok = hmac.compare_digest(password.encode(), self.password.encode())
        return user_ok and password_ok
