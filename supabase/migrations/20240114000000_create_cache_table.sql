-- Create a table to cache API responses
create table if not exists api_cache (
  hash text primary key,
  response jsonb not null,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Enable Row Level Security (RLS) is good practice, but since we use service_role key server-side, it bypasses RLS.
-- However, if we ever access this from client, we might need policies.
-- For now, we can leave it simple.
