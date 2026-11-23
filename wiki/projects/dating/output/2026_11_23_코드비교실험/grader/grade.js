// 채점 시험(실험 땐 양쪽에 비공개). 사용: node grader/grade.js <migration.sql>  (먼저 cd harness && npm install)
const H = require('path').join(__dirname, '../harness/');
const { makeDb, as, sql } = require(H + 'env.js');
const file = process.argv[2];

const U = {
  A: '00000000-0000-0000-0000-00000000000a', B: '00000000-0000-0000-0000-00000000000b',
  C: '00000000-0000-0000-0000-00000000000c', D: '00000000-0000-0000-0000-00000000000d',
  E: '00000000-0000-0000-0000-00000000000e', M: '00000000-0000-0000-0000-0000000000ff',
};
// [이름, 성별, 생일, 선호성별, min, max, 활성+인증]
const PEOPLE = [
  ['A', 'man', '1995-01-01', ['woman'], 19, 40, true],
  ['B', 'woman', '1997-05-05', ['man'], 19, 40, true],
  ['C', 'woman', '1990-03-03', ['man'], 19, 30, true],   // A(31세)는 C의 범위 밖
  ['D', 'woman', '1998-02-02', ['man'], 19, 99, false],  // 미인증
  ['E', 'woman', '2000-07-07', ['man'], 19, 99, true],
];

async function world() {
  const db = await makeDb(file);
  for (const id of Object.values(U)) await sql(db, 'insert into auth.users(id) values ($1)', [id]);
  await sql(db, 'insert into private.admins(user_id) values ($1)', [U.M]);
  for (const [n, g, bd, pg, mn, mx, ok] of PEOPLE) {
    await as(db, U[n], 'insert into public.profiles(id,nickname,gender,region,bio) values ($1,$2,$3,$4,$5)', [U[n], 'nick' + n, g, 'seoul', 'hi']);
    await as(db, U[n], 'insert into public.preferences(user_id,min_age,max_age,genders) values ($1,$2,$3,$4)', [U[n], mn, mx, pg]);
    await as(db, U[n], 'select public.set_birth_date($1)', [bd]);
    if (ok) await sql(db, "update public.member_status set status='active', photo_verified=true where user_id=$1", [U[n]]);
  }
  return db;
}
const throws = async (p) => { try { await p; return false; } catch { return true; } };
const cands = async (db, who) => (await as(db, U[who], 'select * from public.get_candidates(20)')).rows;
const ids = (rows) => rows.map(r => Object.keys(U).find(k => U[k] === r.id)).sort().join('');

const T = [];
const t = (name, fn) => T.push([name, fn]);

t('설치: migration 실행', async () => { await makeDb(file); return true; });
t('프로필 insert 시 member_status가 draft로 자동 생성', async () => {
  const db = await makeDb(file); await sql(db, 'insert into auth.users values ($1)', [U.A]);
  await as(db, U.A, "insert into public.profiles(id,nickname,gender,region) values ($1,'nickA','man','seoul')", [U.A]);
  const r = await sql(db, 'select status, photo_verified from public.member_status where user_id=$1', [U.A]);
  return r.rows.length === 1 && r.rows[0].status === 'draft' && r.rows[0].photo_verified === false;
});
t('남의 id로 프로필 insert 불가', async () => {
  const db = await makeDb(file); await sql(db, 'insert into auth.users values ($1),($2)', [U.A, U.B]);
  return throws(as(db, U.A, "insert into public.profiles(id,nickname,gender,region) values ($1,'nickB','woman','seoul')", [U.B]));
});
t('닉네임 1자는 거부', async () => {
  const db = await makeDb(file); await sql(db, 'insert into auth.users values ($1)', [U.A]);
  return throws(as(db, U.A, "insert into public.profiles(id,nickname,gender,region) values ($1,'x','man','seoul')", [U.A]));
});
t('선호 나이 18은 거부', async () => {
  const db = await world();
  return throws(as(db, U.A, 'update public.preferences set min_age=18 where user_id=$1', [U.A]));
});
t('anon은 profiles를 못 읽음', async () => {
  const db = await world();
  try { const r = await as(db, null, 'select * from public.profiles'); return r.rows.length === 0; } catch { return true; }
});
t('남의 profiles를 직접 못 읽음', async () => {
  const db = await world();
  const r = await as(db, U.A, 'select id from public.profiles');
  return r.rows.every(x => x.id === U.A);
});
t('남의 preferences를 직접 못 읽음', async () => {
  const db = await world();
  const r = await as(db, U.A, 'select user_id from public.preferences');
  return r.rows.length === 1 && r.rows[0].user_id === U.A;
});
t('내 member_status는 읽히고 남의 것은 안 읽힘', async () => {
  const db = await world();
  const r = await as(db, U.A, 'select user_id from public.member_status');
  return r.rows.length === 1 && r.rows[0].user_id === U.A;
});
t('스스로 인증·활성으로 못 바꿈', async () => {
  const db = await world();
  try { await as(db, U.D, "update public.member_status set status='active', photo_verified=true where user_id=$1", [U.D]); } catch {}
  try { await as(db, U.D, "insert into public.member_status(user_id,status,photo_verified) values ($1,'active',true) on conflict (user_id) do update set status='active', photo_verified=true", [U.D]); } catch {}
  const r = await sql(db, 'select photo_verified from public.member_status where user_id=$1', [U.D]);
  return r.rows[0].photo_verified === false;
});
t('내 member_status를 지울 수 없음', async () => {
  const db = await world();
  try { await as(db, U.A, 'delete from public.member_status where user_id=$1', [U.A]); } catch {}
  return (await sql(db, 'select 1 from public.member_status where user_id=$1', [U.A])).rows.length === 1;
});
t('private.user_private 직접 접근 불가', async () => {
  const db = await world();
  return throws(as(db, U.A, 'select * from private.user_private'));
});
t('만 19세 미만 생년월일 거부', async () => {
  const db = await world();
  return throws(as(db, U.A, "select public.set_birth_date('2010-01-01')"));
});
t('생년월일 갱신 동작', async () => {
  const db = await world();
  await as(db, U.A, "select public.set_birth_date('1996-01-01')");
  const r = await sql(db, 'select birth_date::text b from private.user_private where user_id=$1', [U.A]);
  return r.rows[0].b === '1996-01-01';
});
t('운영자 아니면 admin_set_status 오류', async () => {
  const db = await world();
  return throws(as(db, U.D, "select public.admin_set_status($1,'active',true)", [U.D]));
});
t('운영자는 admin_set_status 가능', async () => {
  const db = await world();
  await as(db, U.M, "select public.admin_set_status($1,'active',true)", [U.D]);
  const r = await sql(db, 'select status, photo_verified from public.member_status where user_id=$1', [U.D]);
  return r.rows[0].status === 'active' && r.rows[0].photo_verified === true;
});
t('자격 없으면 get_candidates 오류', async () => {
  const db = await world(); return throws(cands(db, 'D'));
});
t('anon은 get_candidates 못 씀', async () => {
  const db = await world(); return throws(as(db, null, 'select * from public.get_candidates(20)'));
});
t('후보 = 서로 선호 맞는 인증 회원(B,E)', async () => {
  const db = await world(); return ids(await cands(db, 'A')) === 'BE';
});
t('후보의 나이가 만 나이로 맞음', async () => {
  const db = await world();
  const b = (await cands(db, 'A')).find(r => r.id === U.B);
  const d = new Date(), y = d.getFullYear() - 1997 - ((d.getMonth() + 1 < 5 || (d.getMonth() + 1 === 5 && d.getDate() < 5)) ? 1 : 0);
  return b && Number(b.age) === y;
});
t('like한 사람은 후보에서 빠짐', async () => {
  const db = await world(); await as(db, U.A, "select public.swipe($1,'like')", [U.B]);
  return ids(await cands(db, 'A')) === 'E';
});
t('30일 안에 pass한 사람은 빠지고, 지나면 다시 나옴', async () => {
  const db = await world(); await as(db, U.A, "select public.swipe($1,'pass')", [U.B]);
  const a = ids(await cands(db, 'A')) === 'E';
  await sql(db, "update public.swipes set created_at = now() - interval '31 days' where from_id=$1", [U.A]);
  return a && ids(await cands(db, 'A')) === 'BE';
});
t('swipes 직접 insert 불가', async () => {
  const db = await world();
  try { await as(db, U.A, "insert into public.swipes(from_id,to_id,action) values ($1,$2,'like')", [U.A, U.B]); } catch {}
  return (await sql(db, 'select 1 from public.swipes')).rows.length === 0;
});
t('남이 보낸 swipe는 안 보임', async () => {
  const db = await world(); await as(db, U.B, "select public.swipe($1,'like')", [U.A]);
  return (await as(db, U.A, 'select * from public.swipes')).rows.length === 0;
});
t('서로 like → 매칭 1개, 다시 해도 1개', async () => {
  const db = await world();
  const r1 = (await as(db, U.A, "select public.swipe($1,'like') m", [U.B])).rows[0].m;
  const r2 = (await as(db, U.B, "select public.swipe($1,'like') m", [U.A])).rows[0].m;
  try { await as(db, U.B, "select public.swipe($1,'like')", [U.A]); } catch {}
  try { await as(db, U.A, "select public.swipe($1,'like')", [U.B]); } catch {}
  const n = (await sql(db, 'select count(*)::int n from public.matches')).rows[0].n;
  return r1 === null && r2 !== null && n === 1;
});
t('미인증 상대·자기 자신에게 swipe 오류', async () => {
  const db = await world();
  return (await throws(as(db, U.A, "select public.swipe($1,'like')", [U.D]))) && (await throws(as(db, U.A, "select public.swipe($1,'like')", [U.A])));
});
async function matched() {
  const db = await world();
  await as(db, U.A, "select public.swipe($1,'like')", [U.B]);
  const m = (await as(db, U.B, "select public.swipe($1,'like') m", [U.A])).rows[0].m;
  return [db, m];
}
t('매칭 상대는 후보에서 빠짐', async () => {
  const [db] = await matched(); await sql(db, 'delete from public.swipes');
  return !(await cands(db, 'A')).some(r => r.id === U.B);
});
t('매칭은 당사자만 보임', async () => {
  const [db] = await matched();
  return (await as(db, U.A, 'select * from public.matches')).rows.length === 1 && (await as(db, U.E, 'select * from public.matches')).rows.length === 0;
});
t('당사자는 메시지 보내고 읽음', async () => {
  const [db, m] = await matched();
  await as(db, U.A, "select public.send_message($1,'안녕')", [m]);
  return (await as(db, U.B, 'select body from public.messages')).rows[0]?.body === '안녕';
});
t('제3자는 메시지 못 보내고 못 읽음', async () => {
  const [db, m] = await matched();
  await as(db, U.A, "select public.send_message($1,'안녕')", [m]);
  const sent = await throws(as(db, U.E, "select public.send_message($1,'끼어들기')", [m]));
  return sent && (await as(db, U.E, 'select * from public.messages')).rows.length === 0;
});
t('messages 직접 insert 불가', async () => {
  const [db, m] = await matched();
  try { await as(db, U.A, "insert into public.messages(match_id,sender_id,body) values ($1,$2,'x')", [m, U.A]); } catch {}
  return (await sql(db, 'select 1 from public.messages')).rows.length === 0;
});
t('빈 메시지·2001자 메시지 거부', async () => {
  const [db, m] = await matched();
  return (await throws(as(db, U.A, "select public.send_message($1,'')", [m]))) && (await throws(as(db, U.A, 'select public.send_message($1,$2)', [m, 'x'.repeat(2001)])));
});
t('차단하면 매칭 종료 + 메시지 불가', async () => {
  const [db, m] = await matched();
  await as(db, U.B, 'select public.block_user($1)', [U.A]);
  const ended = (await sql(db, 'select ended_at from public.matches where id=$1', [m])).rows[0].ended_at !== null;
  return ended && (await throws(as(db, U.A, "select public.send_message($1,'왜')", [m])));
});
t('차단은 양쪽 후보에서 빠짐 + swipe 불가', async () => {
  const db = await world(); await as(db, U.A, 'select public.block_user($1)', [U.E]);
  const a = !(await cands(db, 'A')).some(r => r.id === U.E), e = !(await cands(db, 'E')).some(r => r.id === U.A);
  return a && e && (await throws(as(db, U.E, "select public.swipe($1,'like')", [U.A])));
});
t('blocks 직접 insert 불가, 남의 차단 안 보임', async () => {
  const db = await world(); await as(db, U.A, 'select public.block_user($1)', [U.E]);
  try { await as(db, U.B, 'insert into public.blocks(blocker_id,blocked_id) values ($1,$2)', [U.B, U.C]); } catch {}
  const n = (await sql(db, 'select count(*)::int n from public.blocks')).rows[0].n;
  return n === 1 && (await as(db, U.E, 'select * from public.blocks')).rows.length === 0;
});
t('탈퇴하면 내 데이터가 연쇄 삭제', async () => {
  const [db, m] = await matched();
  await as(db, U.A, "select public.send_message($1,'안녕')", [m]);
  await as(db, U.A, 'select public.delete_my_account()');
  const left = (await sql(db, `select (select count(*) from auth.users where id=$1) + (select count(*) from public.profiles where id=$1) + (select count(*) from public.matches) + (select count(*) from public.messages) + (select count(*) from private.user_private where user_id=$1) n`, [U.A])).rows[0].n;
  return Number(left) === 0;
});
t('security definer 함수는 search_path 고정', async () => {
  const db = await makeDb(file);
  const r = await sql(db, "select proname, proconfig from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in ('public','private') and prosecdef");
  return r.rows.length > 0 && r.rows.every(x => (x.proconfig || []).some(c => c.startsWith('search_path=')));
});

(async () => {
  let pass = 0; const out = [];
  for (const [name, fn] of T) {
    let ok = false, err = '';
    try { ok = await fn(); } catch (e) { err = String(e.message || e).slice(0, 90); }
    if (ok) pass++;
    out.push(`${ok ? '✅' : '❌'} ${name}${err ? '  (' + err + ')' : ''}`);
  }
  console.log(out.join('\n')); console.log(`\n점수: ${pass}/${T.length}`);
})();
