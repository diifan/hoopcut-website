begin;
create table if not exists public.hc_tracer_jobs (
 id text primary key check(id ~ '^[a-f0-9]{48}$'), environment text not null check(environment in ('staging','production')),
 request_id uuid not null, rate_key text not null, size_bytes bigint not null check(size_bytes between 1 and 536870912),
 state text not null default 'uploading', stage text not null default 'uploading', operation text not null default 'probe',
 progress int not null default 0, video jsonb, trim jsonb, effect text not null default 'firework', renders jsonb not null default '{}',
 lease uuid, lease_until timestamptz, attempts int not null default 0, error text,
 created_at timestamptz not null default now(), updated_at timestamptz not null default now(), expires_at timestamptz not null default now()+interval '24 hours',
 unique(environment,request_id)
);
alter table public.hc_tracer_jobs add column if not exists selection jsonb;
alter table public.hc_tracer_jobs add column if not exists hoop jsonb;
alter table public.hc_tracer_jobs enable row level security;
revoke all on public.hc_tracer_jobs from anon,authenticated;
grant all on public.hc_tracer_jobs to service_role;
create index if not exists hc_tracer_queue on public.hc_tracer_jobs(environment,state,created_at);
create or replace function public.hc_tracer_command(p_env text,p_action text,p_id text,p_data jsonb)
returns jsonb language plpgsql security definer set search_path=public,pg_temp as $$
declare j hc_tracer_jobs; n int; s double precision; e double precision; f text; chosen jsonb;
begin
 if p_env not in ('staging','production') then raise exception 'invalid_environment'; end if;
 perform pg_advisory_xact_lock(hashtext('hc-tracer-'||p_env));
 if p_action='create' then
  select * into j from hc_tracer_jobs where environment=p_env and request_id=(p_data->>'request_id')::uuid;
  if found then
   if j.size_bytes<>(p_data->>'size_bytes')::bigint or j.rate_key<>p_data->>'rate_key' then raise exception 'request_conflict'; end if;
   return to_jsonb(j);
  end if;
  select count(*) into n from hc_tracer_jobs where environment=p_env and rate_key=p_data->>'rate_key' and created_at>now()-interval '1 hour';
  if n>=6 then raise exception 'rate_limited'; end if;
  select count(*) into n from hc_tracer_jobs where environment=p_env and expires_at>now() and state<>'expired';
  if n>=20 or (select coalesce(sum(size_bytes),0) from hc_tracer_jobs where expires_at>now() and state<>'expired')+(p_data->>'size_bytes')::bigint>2147483648 then raise exception 'storage_busy'; end if;
  insert into hc_tracer_jobs(id,environment,request_id,rate_key,size_bytes) values(p_id,p_env,(p_data->>'request_id')::uuid,p_data->>'rate_key',(p_data->>'size_bytes')::bigint) returning * into j;
  return to_jsonb(j);
 elsif p_action='poll' then
  update hc_tracer_jobs set state=case when attempts<2 then 'queued' else 'failed' end,stage=case when attempts<2 then 'queued' else 'failed' end,error='Worker interrupted. Please retry.',lease=null where environment=p_env and state='processing' and lease_until<now();
  if exists(select 1 from hc_tracer_jobs where environment=p_env and state='processing') then return 'null'::jsonb; end if;
  select * into j from hc_tracer_jobs where environment=p_env and state='queued' and expires_at>now() order by created_at limit 1 for update;
  if not found then return 'null'::jsonb; end if;
  update hc_tracer_jobs set state='processing',stage='downloading',lease=gen_random_uuid(),lease_until=now()+interval '120 seconds',attempts=attempts+1,updated_at=now() where id=j.id returning * into j;
  return to_jsonb(j);
 end if;
 select * into j from hc_tracer_jobs where id=p_id and environment=p_env for update;
 if not found then raise exception 'not_found'; end if;
 if j.expires_at<now() then raise exception 'expired'; end if;
 if p_action='status' then return to_jsonb(j); end if;
 if p_action='cancel' then
  update hc_tracer_jobs set state='cancelled',stage='cancelled',lease=null,updated_at=now() where id=p_id returning * into j; return to_jsonb(j);
 end if;
 if p_action in ('heartbeat','finish') then
  if j.state<>'processing' or j.lease is distinct from (p_data->>'lease')::uuid or j.lease_until<now() then raise exception 'lease_expired'; end if;
  if p_action='heartbeat' then
   update hc_tracer_jobs set lease_until=now()+interval '120 seconds',stage=coalesce(p_data->>'stage',stage),progress=greatest(0,least(99,coalesce((p_data->>'progress')::int,progress))),updated_at=now() where id=p_id returning * into j;
  else
   f=p_data->>'state';if f not in ('imported','ready','no_shots','failed','needs_hoop') then raise exception 'invalid_state'; end if;
   update hc_tracer_jobs set state=f,stage=f,progress=case when f in ('ready','no_shots') then 100 else 0 end,video=coalesce(p_data->'video',video),selection=coalesce(p_data->'selection',selection),renders=case when f='ready' then renders||jsonb_build_object(effect,p_data->'render') else renders end,error=p_data->>'error',lease=null,lease_until=null,updated_at=now() where id=p_id returning * into j;
  end if;return to_jsonb(j);
 elsif p_action='complete' then
  if j.state='uploading' then update hc_tracer_jobs set state='queued',stage='queued',operation='probe',attempts=0,updated_at=now() where id=p_id returning * into j; end if;return to_jsonb(j);
 elsif p_action='process' then
  if j.state in ('processing','queued') then raise exception 'job_busy'; end if;
  if j.video is null then raise exception 'video_not_ready'; end if;
  s=(p_data->>'start')::double precision;e=(p_data->>'end')::double precision;f=p_data->>'effect';
  if not (s>=0 and s<e and e<=(j.video->>'duration')::double precision+0.05 and e-s<=30.001) or f not in ('firework','cosmic','ice','sunset') then raise exception 'invalid_range'; end if;
  chosen=null;
  if j.trim=jsonb_build_array(s,e) then
   chosen=j.hoop;
   if p_data ? 'hoop_id' then
    select c into chosen from jsonb_array_elements(j.selection->'candidates') c where c->>'id'=p_data->>'hoop_id';
    if chosen is null then raise exception 'invalid_selection'; end if;
   end if;
  elsif p_data ? 'hoop_id' then raise exception 'invalid_selection'; end if;
  if j.trim=jsonb_build_array(s,e) and j.hoop is not distinct from chosen and j.renders ? f then
   update hc_tracer_jobs set state='ready',stage='ready',progress=100,effect=f,error=null,updated_at=now() where id=p_id returning * into j;return to_jsonb(j);
  end if;
  select count(*) into n from hc_tracer_jobs where environment=p_env and state in ('queued','processing');if n>=3 then raise exception 'queue_busy'; end if;
  update hc_tracer_jobs set state='queued',stage='queued',operation='render',effect=f,hoop=chosen,selection=case when trim=jsonb_build_array(s,e) then selection else null end,renders=case when trim=jsonb_build_array(s,e) and hoop is not distinct from chosen then renders else '{}'::jsonb end,trim=jsonb_build_array(s,e),attempts=0,progress=0,error=null,updated_at=now() where id=p_id returning * into j;return to_jsonb(j);
 end if;
 raise exception 'unknown_action';
end $$;
revoke all on function public.hc_tracer_command(text,text,text,jsonb) from public,anon,authenticated;
grant execute on function public.hc_tracer_command(text,text,text,jsonb) to service_role;
insert into storage.buckets(id,name,public,file_size_limit) values('hoopcut-web-tracer','hoopcut-web-tracer',false,536870912) on conflict(id) do nothing;
commit;
