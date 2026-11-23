// 시험 환경: Supabase 흉내(PGlite). 사용: const {makeDb, as, sql} = require('./env'); const db = await makeDb('path/to/migration.sql')
const { PGlite } = require('@electric-sql/pglite');
const fs = require('fs');

const ENV = `
create role anon nologin; create role authenticated nologin;
create schema auth;
create table auth.users(id uuid primary key);
create function auth.uid() returns uuid language sql stable as $$ select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid $$;
grant usage on schema auth to anon, authenticated;
grant execute on function auth.uid() to anon, authenticated;
grant usage on schema public to anon, authenticated;
alter default privileges in schema public grant all on tables to anon, authenticated;
alter default privileges in schema public grant all on sequences to anon, authenticated;
alter default privileges in schema public grant execute on functions to anon, authenticated;
`;

async function makeDb(migrationPath) {
  const db = new PGlite();
  await db.exec(ENV);
  await db.exec(fs.readFileSync(migrationPath, 'utf8'));
  return db;
}

// 사용자 uid로 SQL 실행(uid=null이면 anon). 끝나면 슈퍼유저로 되돌림.
async function as(db, uid, text, params = []) {
  await db.exec(`reset role; select set_config('request.jwt.claim.sub', '${uid || ''}', false); set role ${uid ? 'authenticated' : 'anon'};`);
  try { return await db.query(text, params); }
  finally { await db.exec(`reset role; select set_config('request.jwt.claim.sub', '', false);`); }
}

// 슈퍼유저로 실행
const sql = (db, text, params = []) => db.query(text, params);

module.exports = { makeDb, as, sql };
