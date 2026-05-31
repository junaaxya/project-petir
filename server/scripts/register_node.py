from __future__ import annotations

import argparse
import secrets
import sys
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.ingest.auth import hash_token
from app.models.registry import EdgeNode
from app.settings import settings


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Register or rotate an edge node token. Prints the plaintext token ONCE."
    )
    parser.add_argument("node_id", help="Stable node id, e.g. rpi-lab-01")
    parser.add_argument("--name", default=None)
    parser.add_argument("--location", default=None)
    parser.add_argument(
        "--rotate",
        action="store_true",
        help="Issue a new token for an existing node; keeps the old hash in previous_token_hash for graceful cutover.",
    )
    parser.add_argument("--database-url", default=settings.database_url)
    args = parser.parse_args(argv[1:])

    token = secrets.token_urlsafe(32)
    token_hash = hash_token(token)

    engine = create_engine(args.database_url, future=True)
    session = sessionmaker(bind=engine, expire_on_commit=False)()

    node = session.get(EdgeNode, args.node_id)
    if node is None:
        node = EdgeNode(
            node_id=args.node_id,
            name=args.name,
            location=args.location,
            api_token_hash=token_hash,
            enabled=True,
        )
        session.add(node)
        action = "created"
    else:
        if args.rotate:
            node.previous_token_hash = node.api_token_hash
            node.token_rotated_at_utc = datetime.now(timezone.utc)
        node.api_token_hash = token_hash
        if args.name is not None:
            node.name = args.name
        if args.location is not None:
            node.location = args.location
        node.enabled = True
        action = "rotated" if args.rotate else "token reset"

    session.commit()
    session.close()

    print(f"node {args.node_id}: {action}")
    print("NODE_TOKEN (copy to edge/.env on the Pi — shown only once):")
    print(token)
    if action == "rotated":
        print("note: the previous token still works until the next rotation (graceful cutover).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
