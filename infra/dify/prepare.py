"""为官方 Dify Compose 初始化本机运行环境。"""

import argparse
import os
import re
import secrets
import sys
from pathlib import Path


def prepare(folder: Path) -> bool:
    dest = folder / ".env"
    if dest.exists():
        return False
    content = (folder / ".env.example").read_text(encoding="utf-8")
    keys = dict.fromkeys(
        (
            "SECRET_KEY",
            "DB_PASSWORD",
            "REDIS_PASSWORD",
            "PLUGIN_DAEMON_KEY",
            "PLUGIN_DIFY_INNER_API_KEY",
            "DIFY_AGENT_SERVER_SECRET_KEY",
            "DIFY_AGENT_LOCAL_SANDBOX_AUTH_TOKEN",
        )
    )
    values = {key: secrets.token_urlsafe(32) for key in keys}
    sandbox = secrets.token_urlsafe(32)
    weaviate = secrets.token_urlsafe(32)
    values.update(
        COMPOSE_PROJECT_NAME="grounded_dify",
        COMPOSE_PROFILES="weaviate,postgresql,collaboration",
        DB_TYPE="postgresql",
        VECTOR_STORE="weaviate",
        SSRF_PROXY_HTTP_URL="http://ssrf_proxy:3128",
        SSRF_PROXY_HTTPS_URL="http://ssrf_proxy:3128",
        SANDBOX_API_KEY=sandbox,
        CODE_EXECUTION_API_KEY=sandbox,
        WEAVIATE_API_KEY=weaviate,
        WEAVIATE_AUTHENTICATION_APIKEY_ALLOWED_KEYS=weaviate,
    )
    for name, value in values.items():
        pattern = rf"^{re.escape(name)}=.*$"
        content, count = re.subn(
            pattern, f"{name}={value}", content, flags=re.MULTILINE
        )
        if count == 0:
            content = content.rstrip("\n") + f"\n{name}={value}\n"
    descriptor = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        output.write(content)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("docker_folder", type=Path)
    args = parser.parse_args()
    created = prepare(args.docker_folder)
    sys.stdout.write(
        "已生成本机 Dify 运行环境。\n" if created else "沿用已有本机 Dify 运行环境。\n"
    )


if __name__ == "__main__":
    main()
