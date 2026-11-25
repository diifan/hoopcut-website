import {readFileSync} from 'node:fs';
import pg from 'pg';
if(!process.env.TIKTOK_MIGRATION_DATABASE_URL)throw new Error('Use an authorized database administrator connection via TIKTOK_MIGRATION_DATABASE_URL, or execute migrate-tiktok.sql through the existing Supabase management session. The website runtime cannot create schemas.');
const db=new pg.Pool({connectionString:process.env.TIKTOK_MIGRATION_DATABASE_URL,ssl:{ca:readFileSync(new URL('../lib/supabase-ca.crt',import.meta.url),'utf8'),rejectUnauthorized:true},max:1,connectionTimeoutMillis:10000});
try{await db.query(readFileSync(new URL('./migrate-tiktok.sql',import.meta.url),'utf8'));console.log('TikTok schema ready; table access restricted, RLS enabled.');}catch{console.error('TikTok migration failed; check administrator access. No credentials logged.');process.exitCode=1;}finally{await db.end();}
