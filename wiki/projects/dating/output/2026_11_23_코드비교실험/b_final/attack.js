// 공격·재현 시험 (Claude 검토용). node attack.js
const { makeDb, as, sql } = require('../harness/env');
const path = require('path');
const A='00000000-0000-0000-0000-00000000000a',B='00000000-0000-0000-0000-00000000000b',X='00000000-0000-0000-0000-0000000000ff',Z='00000000-0000-0000-0000-00000000000f';
const tryq = async (label, p) => { try { const r = await p; console.log('OK  ', label, JSON.stringify(r.rows)); } catch (e) { console.log('FAIL', label, '-', e.message); } };
(async () => {
  const db = await makeDb(path.join(__dirname, 'migration.sql'));
  for (const u of [A,B,X,Z]) await sql(db,'insert into auth.users(id) values ($1)',[u]);
  await sql(db,'insert into private.admins values ($1)',[X]);
  for (const [u,g] of [[A,'man'],[B,'woman']]) {
    await as(db,u,"insert into public.profiles(id,nickname,gender,region) values ($1,'nick','"+g+"','s')",[u]);
    await as(db,u,"select public.set_birth_date('1995-01-01')");
    await as(db,X,"select public.admin_set_status($1,'active',true)",[u]);
  }
  await tryq('trigger fn direct call', as(db,A,'select private.handle_new_profile()'));
  await tryq('anon call via named arg', as(db,null,'select * from public.get_candidates(lim=>1)'));
  await tryq('admin activates profileless user Z', as(db,X,"select public.admin_set_status($1,'active',true)",[Z]));
  await tryq('profileless Z swipes A', as(db,Z,"select public.swipe($1,'like')",[A]));
  await tryq('oracle: swipe error reveals eligibility of random uuid', as(db,A,"select public.swipe('00000000-0000-0000-0000-000000000123','like')"));
  await as(db,B,'select public.block_user($1)',[A]);
  await tryq('oracle: A learns B blocked A', as(db,A,"select public.swipe($1,'like')",[B]));
  await tryq('A changes birth_date after verification (no limit)', as(db,A,"select public.set_birth_date('0001-01-01')"));
  await tryq('advisory lock available', sql(db,"select pg_advisory_xact_lock(hashtextextended('x',0))"));
  await db.close();
})();
