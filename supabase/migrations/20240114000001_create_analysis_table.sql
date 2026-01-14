-- Create a table to cache Session Analysis
create table if not exists session_analysis (
  session_id text primary key,
  analysis jsonb not null,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);
