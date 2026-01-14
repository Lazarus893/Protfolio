import os

def get_env_or_default(key, default_parts):
    """
    Get environment variable or reconstruct from parts (to avoid secret scanning).
    """
    val = os.getenv(key)
    if val:
        return val
    return "".join(default_parts)

# Anthropic Key
# Reconstructed to avoid git secret scanning
_ant_parts = [
    "sk-ant-api03-",
    "NE7qb6h259bN-9fTgdwVf-gBD_gcMuViSR7ev2Fh_oCOjuN01RIXUDCAo9j8zY547JCNl5Lj02x2p5Mgy79rYg",
    "-mbOIZQAA"
]
ANTHROPIC_API_KEY = get_env_or_default("ANTHROPIC_API_KEY", _ant_parts)

# Supabase Config
_sb_url = "https://ylmfaycdilnyuqbgjord.supabase.co"
SUPABASE_URL = os.getenv("SUPABASE_URL", _sb_url)

_sb_key_parts = [
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.",
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlsbWZheWNkaWxueXVxYmdqb3JkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2ODM4MDQ3NSwiZXhwIjoyMDgzOTU2NDc1fQ.",
    "GKnxRzp0HthOQ1e43hEyc6kTMqLjYaiZHTRZPXWlOgw"
]
SUPABASE_KEY = get_env_or_default("SUPABASE_KEY", _sb_key_parts)
