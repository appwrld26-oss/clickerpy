from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import stat
import sys
from pathlib import Path

import psycopg2
import tomllib

SECRETS_PATH = Path('/home/ubuntu/.streamlit/secrets.toml')
CREDENTIALS_PATH = Path('/home/ubuntu/admin_credentials.txt')
ITERATIONS = 310_000
USERNAME = 'admin'


def make_hash(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, ITERATIONS)
    return f'{salt.hex()}${digest.hex()}'


def verify(password: str, encoded: str) -> bool:
    salt_hex, digest_hex = encoded.split('$', 1)
    actual = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt_hex), ITERATIONS)
    return hmac.compare_digest(actual, bytes.fromhex(digest_hex))


def set_mode_600(path: Path) -> None:
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def update_auth_hash(password_hash: str) -> None:
    raw = SECRETS_PATH.read_text(encoding='utf-8') if SECRETS_PATH.exists() else ''
    lines = raw.splitlines()
    output = []
    in_auth = False
    replaced = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('['):
            in_auth = stripped == '[auth]'
        if in_auth and stripped.startswith('password_hash'):
            output.append(f'password_hash = "{password_hash}"')
            replaced = True
        else:
            output.append(line)
    if not replaced:
        if output and output[-1].strip():
            output.append('')
        output.extend(['[auth]', f'username = "{USERNAME}"', f'password_hash = "{password_hash}"'])
    SECRETS_PATH.write_text('\n'.join(output) + '\n', encoding='utf-8')
    set_mode_600(SECRETS_PATH)


def main() -> int:
    if not SECRETS_PATH.exists():
        print('FAIL: Streamlit secrets file does not exist')
        return 1

    secrets_data = tomllib.loads(SECRETS_PATH.read_text(encoding='utf-8'))
    db_url = secrets_data.get('database', {}).get('url')
    if not db_url:
        print('FAIL: database.url is missing')
        return 1
    if 'sslmode=' not in db_url.lower():
        print('FAIL: database URL does not specify SSL mode')
        return 1

    # Generate and persist a strong random password without printing it.
    password = secrets.token_urlsafe(32)
    password_hash = make_hash(password)
    update_auth_hash(password_hash)
    CREDENTIALS_PATH.write_text(
        'username=' + USERNAME + '\n' + 'password=' + password + '\n',
        encoding='utf-8',
    )
    set_mode_600(CREDENTIALS_PATH)

    auth_data = tomllib.loads(SECRETS_PATH.read_text(encoding='utf-8')).get('auth', {})
    if auth_data.get('username') != USERNAME or not verify(password, auth_data.get('password_hash', '')):
        print('FAIL: generated credentials failed local verification')
        return 1
    print('PASS: generated admin password hash and local login verification')

    try:
        conn = psycopg2.connect(db_url, connect_timeout=10, application_name='myclicker_validation')
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT 1')
                result = cur.fetchone()[0]
            if result != 1:
                print('FAIL: PostgreSQL returned an unexpected result')
                return 1
        finally:
            conn.close()
        print('PASS: PostgreSQL TLS connection and SELECT 1')
    except Exception as exc:
        print(f'FAIL: PostgreSQL connection test: {type(exc).__name__}: {exc}')
        return 1

    print(f'PASS: secrets permissions {oct(SECRETS_PATH.stat().st_mode & 0o777)}')
    print(f'PASS: credentials permissions {oct(CREDENTIALS_PATH.stat().st_mode & 0o777)}')
    print('Credential material is stored locally only and was not printed.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
