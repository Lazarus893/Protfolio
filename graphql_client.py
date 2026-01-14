#!/usr/bin/env python3
"""
GraphQL Client for Alva LLM API

A command-line tool to query sessions and dialogs from the Alva LLM GraphQL API.
"""

import argparse
import json
import os
import sys
from typing import List, Optional

try:
    import requests
except ImportError:
    print("Error: 'requests' library is required.")
    print("Install it with: pip install requests")
    sys.exit(1)


# Default configuration
DEFAULT_ENDPOINT = "https://api-llm-internal.prd.alva.xyz/query"
DEFAULT_TOKEN = os.getenv("ALVA_API_TOKEN", "")


class GraphQLClient:
    """Simple GraphQL client for the Alva LLM API."""

    def __init__(self, endpoint: str, token: str):
        self.endpoint = endpoint
        self.token = token

    def query_sessions(
        self,
        created_at_start: int,
        created_at_end: int,
        limit: int = 20,
        offset: int = 0,
        show_admin: bool = False,
        show_deleted: bool = False,
    ) -> dict:
        """
        Query sessions from the API.

        Args:
            created_at_start: Unix timestamp for start date filter
            created_at_end: Unix timestamp for end date filter
            limit: Maximum number of results to return
            offset: Number of results to skip
            show_admin: Include admin sessions
            show_deleted: Include deleted sessions

        Returns:
            dict: The GraphQL response data
        """
        input_fields = [
            f"limit: {limit}",
            f"offset: {offset}",
            f"showAdmin: {str(show_admin).lower()}",
            f"showDeleted: {str(show_deleted).lower()}",
            f"createdAtStart: {created_at_start}",
            f"createdAtEnd: {created_at_end}",
        ]
        input_str = ", ".join(input_fields)

        query = f"""
        query {{
            QuerySessions(input: {{{input_str}}}) {{
                totalCount
                list {{
                    id
                }}
            }}
        }}
        """

        return self._execute_query(query)

    def query_dialogs(
        self,
        sid: str,
        created_at_start: int,
        created_at_end: int,
        limit: int = 100,
        offset: int = 0,
        show_admin: bool = True,
        show_deleted: bool = True,
    ) -> dict:
        """
        Query dialogs for a specific session.

        Args:
            sid: Session ID
            created_at_start: Unix timestamp for start date filter
            created_at_end: Unix timestamp for end date filter
            limit: Maximum number of results to return
            offset: Number of results to skip
            show_admin: Include admin dialogs
            show_deleted: Include deleted dialogs

        Returns:
            dict: The GraphQL response data
        """
        input_fields = [
            f'sid: "{sid}"',
            f"limit: {limit}",
            f"offset: {offset}",
            f"showAdmin: {str(show_admin).lower()}",
            f"showDeleted: {str(show_deleted).lower()}",
            f"createdAtStart: {created_at_start}",
            f"createdAtEnd: {created_at_end}",
        ]
        input_str = ", ".join(input_fields)

        query = f"""
        query {{
            Result: QueryDialogs(input: {{{input_str}}}) {{
                totalCount
                list {{
                    qid
                    uid
                    sid
                    skillId
                    question
                    error
                    createdAt
                    updatedAt
                    deletedAt
                    platform
                    answer
                }}
            }}
        }}
        """

        return self._execute_query(query)

    def query_dialogs_for_sessions(
        self,
        session_ids: List[str],
        created_at_start: int,
        created_at_end: int,
        limit: int = 100,
        show_admin: bool = True,
        show_deleted: bool = True,
    ) -> dict:
        """
        Query dialogs for multiple sessions and group by session.

        Args:
            session_ids: List of session IDs
            created_at_start: Unix timestamp for start date filter
            created_at_end: Unix timestamp for end date filter
            limit: Maximum number of results per session
            show_admin: Include admin dialogs
            show_deleted: Include deleted dialogs

        Returns:
            dict: Grouped dialogs by session ID
        """
        result = {"sessions": {}}

        for sid in session_ids:
            try:
                dialogs_response = self.query_dialogs(
                    sid=sid,
                    created_at_start=created_at_start,
                    created_at_end=created_at_end,
                    limit=limit,
                    show_admin=show_admin,
                    show_deleted=show_deleted,
                )
                result["sessions"][sid] = dialogs_response.get("data", {}).get("Result", {})
            except Exception as e:
                result["sessions"][sid] = {"error": str(e)}

        return result

    def _execute_query(self, query: str) -> dict:
        """Execute a GraphQL query and return the response."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": self.token,
        }

        payload = {"query": query.strip()}

        response = requests.post(self.endpoint, json=payload, headers=headers)
        response.raise_for_status()

        data = response.json()

        if "errors" in data:
            raise RuntimeError(f"GraphQL errors: {data['errors']}")

        return data


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Query sessions and dialogs from Alva LLM GraphQL API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Query sessions only
  python %(prog)s --start 1765702597 --end 1768380997

  # Query sessions and their dialogs
  python %(prog)s --start 1765702597 --end 1768380997 --include-dialogs

  # Query dialogs for specific session IDs
  python %(prog)s --session-ids 2011360358991888384,2011336037569363968 --include-dialogs

  # Query dialogs for a single session
  python %(prog)s --sid 2011360358991888384 --dialogs-only
        """,
    )

    parser.add_argument(
        "--endpoint",
        default=DEFAULT_ENDPOINT,
        help=f"API endpoint URL (default: {DEFAULT_ENDPOINT})",
    )
    parser.add_argument(
        "--token",
        default=DEFAULT_TOKEN,
        help="Authorization token (default: from ALVA_API_TOKEN env var)",
    )

    # Session query arguments
    parser.add_argument(
        "--limit", type=int, default=20, help="Maximum number of sessions (default: 20)"
    )
    parser.add_argument(
        "--offset", type=int, default=0, help="Number of sessions to skip (default: 0)"
    )
    parser.add_argument(
        "--show-admin-sessions",
        action="store_true",
        help="Include admin sessions in results",
    )
    parser.add_argument(
        "--show-deleted-sessions",
        action="store_true",
        help="Include deleted sessions in results",
    )

    # Date range (required for session queries)
    parser.add_argument(
        "--start",
        type=int,
        dest="created_at_start",
        help="Start date filter (Unix timestamp)",
    )
    parser.add_argument(
        "--end",
        type=int,
        dest="created_at_end",
        help="End date filter (Unix timestamp)",
    )

    # Dialog query arguments
    parser.add_argument(
        "--include-dialogs",
        action="store_true",
        help="When querying sessions, also fetch their dialogs",
    )
    parser.add_argument(
        "--dialogs-only",
        action="store_true",
        help="Only query dialogs, skip session query (requires --sid)",
    )
    parser.add_argument(
        "--sid",
        help="Query dialogs for a specific session ID",
    )
    parser.add_argument(
        "--session-ids",
        help="Comma-separated list of session IDs to query dialogs for",
    )
    parser.add_argument(
        "--dialog-limit",
        type=int,
        default=100,
        help="Maximum dialogs per session (default: 100)",
    )

    # Output options
    parser.add_argument(
        "--pretty", action="store_true", help="Pretty print JSON output"
    )
    parser.add_argument(
        "--output", "-o", help="Write output to file instead of stdout"
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_arguments()

    # Validate token
    if not args.token:
        print(
            "Error: Authorization token is required.",
            file=sys.stderr,
        )
        print(
            "Set it via --token argument or ALVA_API_TOKEN environment variable.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Create client
    client = GraphQLClient(args.endpoint, args.token)

    result = None

    try:
        # Mode 1: Query dialogs for a single session
        if args.dialogs_only:
            if not args.sid:
                print("Error: --sid is required when using --dialogs-only", file=sys.stderr)
                sys.exit(1)

            # Use date range from args or defaults
            start = args.created_at_start or 0
            end = args.created_at_end or 4102416000

            result = client.query_dialogs(
                sid=args.sid,
                created_at_start=start,
                created_at_end=end,
                limit=args.dialog_limit,
            )

        # Mode 2: Query dialogs for specific session IDs
        elif args.session_ids:
            start = args.created_at_start or 0
            end = args.created_at_end or 4102416000

            session_ids = [s.strip() for s in args.session_ids.split(",")]
            result = client.query_dialogs_for_sessions(
                session_ids=session_ids,
                created_at_start=start,
                created_at_end=end,
                limit=args.dialog_limit,
            )

        # Mode 3: Query sessions (optionally with dialogs)
        else:
            if not args.created_at_start or not args.created_at_end:
                print(
                    "Error: --start and --end are required when querying sessions",
                    file=sys.stderr,
                )
                sys.exit(1)

            # First query sessions
            sessions_response = client.query_sessions(
                limit=args.limit,
                offset=args.offset,
                show_admin=args.show_admin_sessions,
                show_deleted=args.show_deleted_sessions,
                created_at_start=args.created_at_start,
                created_at_end=args.created_at_end,
            )

            if args.include_dialogs:
                # Extract session IDs
                session_list = sessions_response.get("data", {}).get("QuerySessions", {}).get("list", [])
                session_ids = [s["id"] for s in session_list]

                # Query dialogs for each session
                dialogs_result = client.query_dialogs_for_sessions(
                    session_ids=session_ids,
                    created_at_start=args.created_at_start,
                    created_at_end=args.created_at_end,
                    limit=args.dialog_limit,
                )

                # Combine results
                result = {
                    "sessions": sessions_response.get("data", {}).get("QuerySessions", {}),
                    "dialogs": dialogs_result.get("sessions", {}),
                }
            else:
                result = sessions_response

    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}", file=sys.stderr)
        if e.response is not None:
            try:
                print(f"Response: {e.response.text}", file=sys.stderr)
            except:
                pass
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the API endpoint.", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Output results
    output = json.dumps(result, indent=2 if args.pretty else None, ensure_ascii=False)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Results written to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
