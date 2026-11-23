const assert = require('assert');
const path = require('path');
const { makeDb, as, sql } = require('../harness/env');

const MIGRATION = path.join(__dirname, 'migration.sql');

const uid = (n) => `00000000-0000-0000-0000-${String(n).padStart(12, '0')}`;

async function expectFail(promise, label) {
  let failed = false;
  try {
    await promise;
  } catch (err) {
    failed = true;
  }
  assert.strictEqual(failed, true, `Expected failure but succeeded: ${label}`);
}

async function createUser(db, id) {
  await sql(db, 'insert into auth.users(id) values ($1)', [id]);
}

async function setupFullUser(db, adminId, id, {
  nickname = 'user' + id.slice(-2),
  gender = 'man',
  region = 'seoul',
  bio = 'hello',
  birthDate = '1996-01-01',
  minAge = 20,
  maxAge = 40,
  genders = ['woman'],
  status = 'active',
  verified = true,
} = {}) {
  await createUser(db, id);
  await as(db, id,
    'insert into public.profiles(id, nickname, gender, region, bio) values ($1, $2, $3, $4, $5)',
    [id, nickname, gender, region, bio]
  );
  if (birthDate !== null) {
    await as(db, id, 'select public.set_birth_date($1)', [birthDate]);
  }
  if (genders !== null) {
    await as(db, id,
      'insert into public.preferences(user_id, min_age, max_age, genders) values ($1, $2, $3, $4)',
      [id, minAge, maxAge, genders]
    );
  }
  if (status !== 'draft' || verified !== false) {
    await as(db, adminId, 'select public.admin_set_status($1, $2, $3)', [id, status, verified]);
  }
}

async function run() {
  const db = await makeDb(MIGRATION);
  const ADMIN = uid(1);
  const A = uid(2);
  const B = uid(3);
  const C = uid(4);

  await createUser(db, ADMIN);
  await sql(db, 'insert into private.admins(user_id) values ($1)', [ADMIN]);

  // 1. Metadata & security posture audit
  {
    const procs = (await sql(db, `
      select p.oid, p.proname, pg_get_function_identity_arguments(p.oid) as args,
             p.prosecdef, p.proconfig,
             has_function_privilege('anon', p.oid, 'EXECUTE') as anon_exec,
             has_function_privilege('public', p.oid, 'EXECUTE') as pub_exec,
             has_function_privilege('authenticated', p.oid, 'EXECUTE') as auth_exec
      from pg_proc p
      join pg_namespace n on n.oid = p.pronamespace
      where n.nspname = 'public'
      order by p.proname
    `)).rows;

    const expectedFns = [
      'admin_set_status',
      'block_user',
      'delete_my_account',
      'get_candidates',
      'send_message',
      'set_birth_date',
      'swipe',
    ];
    assert.deepStrictEqual(procs.map((p) => p.proname), expectedFns, 'Exact 7 public functions');
    for (const p of procs) {
      assert.strictEqual(p.prosecdef, true, `${p.proname} must be security definer`);
      assert.ok(Array.isArray(p.proconfig) && p.proconfig.some((c) => c.startsWith('search_path=')), `${p.proname} must fix search_path`);
      assert.strictEqual(p.anon_exec, false, `anon must not execute ${p.proname}`);
      assert.strictEqual(p.pub_exec, false, `public must not execute ${p.proname}`);
      assert.strictEqual(p.auth_exec, true, `authenticated must execute ${p.proname}`);
    }

    const tables = (await sql(db, `
      select n.nspname || '.' || c.relname as fqname, c.relrowsecurity,
             has_table_privilege('anon', c.oid, 'SELECT') as anon_sel,
             has_table_privilege('anon', c.oid, 'INSERT') as anon_ins,
             has_table_privilege('anon', c.oid, 'UPDATE') as anon_upd,
             has_table_privilege('anon', c.oid, 'DELETE') as anon_del,
             has_table_privilege('anon', c.oid, 'TRUNCATE') as anon_trunc,
             has_table_privilege('authenticated', c.oid, 'DELETE') as auth_del,
             has_table_privilege('authenticated', c.oid, 'TRUNCATE') as auth_trunc
      from pg_class c
      join pg_namespace n on n.oid = c.relnamespace
      where c.relkind = 'r' and n.nspname in ('public', 'private')
      order by fqname
    `)).rows;

    assert.strictEqual(tables.length, 9, '9 tables across public and private');
    for (const t of tables) {
      assert.strictEqual(t.relrowsecurity, true, `RLS must be enabled on ${t.fqname}`);
      assert.strictEqual(t.anon_sel, false, `anon SELECT revoked on ${t.fqname}`);
      assert.strictEqual(t.anon_ins, false, `anon INSERT revoked on ${t.fqname}`);
      assert.strictEqual(t.anon_upd, false, `anon UPDATE revoked on ${t.fqname}`);
      assert.strictEqual(t.anon_del, false, `anon DELETE revoked on ${t.fqname}`);
      assert.strictEqual(t.anon_trunc, false, `anon TRUNCATE revoked on ${t.fqname}`);
      assert.strictEqual(t.auth_del, false, `authenticated DELETE revoked on ${t.fqname}`);
      assert.strictEqual(t.auth_trunc, false, `authenticated TRUNCATE revoked on ${t.fqname}`);
    }
  }
  console.log('1. Metadata & security posture audit: PASS');

  // 2. Profile constraints & trigger
  {
    await createUser(db, A);
    await expectFail(as(db, A, "insert into public.profiles(id,nickname,gender,region) values ($1,'a','man','seoul')", [A]), '1-char nickname');
    await expectFail(as(db, A, "insert into public.profiles(id,nickname,gender,region) values ($1,$2,'man','seoul')", [A, 'a'.repeat(21)]), '21-char nickname');
    await expectFail(as(db, A, "insert into public.profiles(id,nickname,gender,region) values ($1,'ab','other','seoul')", [A]), 'invalid gender');
    await expectFail(as(db, A, "insert into public.profiles(id,nickname,gender,region,bio) values ($1,'ab','man','seoul',$2)", [A, 'x'.repeat(501)]), '501-char bio');
    // Can't insert someone else's profile
    await createUser(db, B);
    await expectFail(as(db, A, "insert into public.profiles(id,nickname,gender,region) values ($1,'nickB','woman','seoul')", [B]), 'insert other profile');

    // Valid profile insert (2 Korean chars, default bio '')
    await as(db, A, "insert into public.profiles(id,nickname,gender,region) values ($1,'철수','man','seoul')", [A]);
    const profA = (await as(db, A, 'select * from public.profiles')).rows;
    assert.strictEqual(profA.length, 1);
    assert.strictEqual(profA[0].bio, '');

    // Trigger auto-created member_status with draft / false
    const msA = (await as(db, A, 'select * from public.member_status')).rows;
    assert.deepStrictEqual(msA, [{ user_id: A, status: 'draft', photo_verified: false }]);

    // Update own profile works (20 chars, 500 bio), updating id to B fails
    await as(db, A, 'update public.profiles set nickname=$1, bio=$2 where id=$3', ['가'.repeat(20), 'b'.repeat(500), A]);
    await expectFail(as(db, A, 'update public.profiles set id=$1 where id=$2', [B, A]), 'hijack profile id');
    await expectFail(as(db, A, 'delete from public.profiles where id=$1', [A]), 'direct delete profile');
    await expectFail(as(db, A, 'truncate public.profiles'), 'truncate profile');
  }
  console.log('2. Profile constraints & auto member_status trigger: PASS');

  // 3. member_status protection & admin_set_status
  {
    await expectFail(as(db, A, "update public.member_status set status='active', photo_verified=true where user_id=$1", [A]), 'direct update member_status');
    await expectFail(as(db, A, "insert into public.member_status(user_id,status,photo_verified) values ($1,'active',true)", [B]), 'direct insert member_status');
    await expectFail(as(db, A, "select public.admin_set_status($1,'active',true)", [A]), 'non-admin calling admin_set_status');
    await expectFail(as(db, A, 'insert into private.admins(user_id) values ($1)', [A]), 'insert into private.admins');
    await expectFail(as(db, A, 'select * from private.admins'), 'select private.admins');

    // Admin sets status
    await as(db, ADMIN, "select public.admin_set_status($1,'active',true)", [A]);
    const msA = (await as(db, A, 'select * from public.member_status')).rows;
    assert.deepStrictEqual(msA, [{ user_id: A, status: 'active', photo_verified: true }]);

    // Admin invalid status fails
    await expectFail(as(db, ADMIN, "select public.admin_set_status($1,'vip',true)", [A]), 'invalid status');

    // Admin sets status before B inserts profile -> trigger preserves admin status
    await as(db, ADMIN, "select public.admin_set_status($1,'active',true)", [B]);
    await as(db, B, "insert into public.profiles(id,nickname,gender,region) values ($1,'영희','woman','busan')", [B]);
    const msB = (await as(db, B, 'select * from public.member_status')).rows;
    assert.deepStrictEqual(msB, [{ user_id: B, status: 'active', photo_verified: true }]);

    // A cannot see B's profile or member_status
    assert.strictEqual((await as(db, A, 'select * from public.profiles')).rows.length, 1);
    assert.strictEqual((await as(db, A, 'select * from public.member_status')).rows.length, 1);
  }
  console.log('3. member_status protection & admin_set_status: PASS');

  // 4. set_birth_date & private.user_private isolation & age boundary
  {
    const todayRes = (await sql(db, `
      select
        (current_date - interval '19 years')::date as exactly19,
        ((current_date - interval '19 years') + interval '1 day')::date as almost19,
        (current_date + interval '1 day')::date as tomorrow
    `)).rows[0];

    await expectFail(as(db, A, 'select public.set_birth_date($1)', [todayRes.almost19]), '18y 364d underage');
    await expectFail(as(db, A, 'select public.set_birth_date($1)', [todayRes.tomorrow]), 'future birth_date');
    await expectFail(as(db, A, 'select public.set_birth_date(null)'), 'null birth_date');

    // Exactly 19 today -> succeeds
    await as(db, A, 'select public.set_birth_date($1)', [todayRes.exactly19]);
    // Update existing birth_date -> succeeds
    await as(db, A, "select public.set_birth_date('1996-05-01')");
    await as(db, B, "select public.set_birth_date('1998-05-01')");

    // Cannot read/write private.user_private directly
    await expectFail(as(db, A, 'select * from private.user_private'), 'select private.user_private');
    await expectFail(as(db, A, "insert into private.user_private values ($1,'1990-01-01')", [A]), 'insert private.user_private');

    // pg_temp search_path hijacking attempt against set_birth_date
    await expectFail(as(db, A, `
      create function pg_temp.age(date, date) returns interval language sql as $$ select interval '30 years' $$;
      select public.set_birth_date('2020-01-01');
    `), 'pg_temp age hijack');
  }
  console.log('4. set_birth_date, age boundary & private isolation: PASS');

  // 5. preferences constraints & RLS
  {
    await expectFail(as(db, A, "insert into public.preferences(user_id,min_age,max_age,genders) values ($1,18,30,array['woman'])", [A]), 'min_age < 19');
    await expectFail(as(db, A, "insert into public.preferences(user_id,min_age,max_age,genders) values ($1,20,100,array['woman'])", [A]), 'max_age > 99');
    await expectFail(as(db, A, "insert into public.preferences(user_id,min_age,max_age,genders) values ($1,35,30,array['woman'])", [A]), 'min > max');
    await expectFail(as(db, A, "insert into public.preferences(user_id,genders) values ($1,array['alien'])", [A]), 'invalid gender in prefs');
    await expectFail(as(db, A, "insert into public.preferences(user_id,genders) values ($1,array['woman',null])", [A]), 'null in genders');
    await expectFail(as(db, A, "insert into public.preferences(user_id,genders) values ($1,array['man'])", [B]), 'insert other preferences');

    // Default min_age=19, max_age=99
    await as(db, A, "insert into public.preferences(user_id,genders) values ($1,array['woman'])", [A]);
    const pA = (await as(db, A, 'select * from public.preferences')).rows[0];
    assert.strictEqual(pA.min_age, 19);
    assert.strictEqual(pA.max_age, 99);

    await as(db, A, 'update public.preferences set min_age=25, max_age=35 where user_id=$1', [A]);
    await as(db, B, "insert into public.preferences(user_id,min_age,max_age,genders) values ($1,25,35,array['man'])", [B]);

    // A cannot see B's preferences or update B's preferences
    assert.strictEqual((await as(db, A, 'select * from public.preferences')).rows.length, 1);
    await as(db, A, 'update public.preferences set min_age=19 where user_id=$1', [B]);
    const pB = (await as(db, B, 'select * from public.preferences')).rows[0];
    assert.strictEqual(pB.min_age, 25);
  }
  console.log('5. preferences constraints & RLS: PASS');

  // 6. anon completely blocked on every table & every function
  {
    for (const tbl of [
      'public.profiles', 'public.member_status', 'public.preferences',
      'public.swipes', 'public.matches', 'public.messages', 'public.blocks',
      'private.user_private', 'private.admins',
    ]) {
      await expectFail(as(db, null, `select * from ${tbl}`), `anon select ${tbl}`);
      await expectFail(as(db, null, `truncate ${tbl}`), `anon truncate ${tbl}`);
    }
    await expectFail(as(db, null, "select public.set_birth_date('1990-01-01')"), 'anon set_birth_date');
    await expectFail(as(db, null, "select public.admin_set_status($1,'active',true)", [A]), 'anon admin_set_status');
    await expectFail(as(db, null, 'select * from public.get_candidates()'), 'anon get_candidates');
    await expectFail(as(db, null, "select public.swipe($1,'like')", [B]), 'anon swipe');
    await expectFail(as(db, null, "select public.send_message($1,'hi')", [uid(99)]), 'anon send_message');
    await expectFail(as(db, null, 'select public.block_user($1)', [B]), 'anon block_user');
    await expectFail(as(db, null, 'select public.delete_my_account()'), 'anon delete_my_account');
  }
  console.log('6. anon complete block on tables & functions: PASS');

  // 7. get_candidates comprehensive filtering
  {
    const db2 = await makeDb(MIGRATION);
    await createUser(db2, ADMIN);
    await sql(db2, 'insert into private.admins(user_id) values ($1)', [ADMIN]);

    // Caller M1: man, age ~30 (born 30 years ago), wants woman 25..35
    const yAgo = async (years) =>
      (await sql(db2, `select (current_date - ($1 || ' years')::interval)::date as d`, [years])).rows[0].d;

    const M1 = uid(10);
    await setupFullUser(db2, ADMIN, M1, {
      nickname: 'me', gender: 'man', birthDate: await yAgo(30), minAge: 25, maxAge: 35, genders: ['woman'],
    });

    // U_OK1: woman 25 (min boundary), wants man 30..30 (exact boundary) -> INCLUDE
    const U_OK1 = uid(11);
    await setupFullUser(db2, ADMIN, U_OK1, {
      nickname: 'ok1', gender: 'woman', birthDate: await yAgo(25), minAge: 30, maxAge: 30, genders: ['man'],
    });
    // U_OK2: woman 35 (max boundary), wants man/woman 20..40 -> INCLUDE
    const U_OK2 = uid(12);
    await setupFullUser(db2, ADMIN, U_OK2, {
      nickname: 'ok2', gender: 'woman', birthDate: await yAgo(35), minAge: 20, maxAge: 40, genders: ['man', 'woman'],
    });
    // U_DRAFT: draft + verified -> EXCLUDE
    await setupFullUser(db2, ADMIN, uid(13), {
      nickname: 'draft', gender: 'woman', birthDate: await yAgo(28), minAge: 20, maxAge: 40, genders: ['man'], status: 'draft', verified: true,
    });
    // U_SUSP: suspended + verified -> EXCLUDE
    await setupFullUser(db2, ADMIN, uid(14), {
      nickname: 'susp', gender: 'woman', birthDate: await yAgo(28), minAge: 20, maxAge: 40, genders: ['man'], status: 'suspended', verified: true,
    });
    // U_UNVER: active + unverified -> EXCLUDE
    await setupFullUser(db2, ADMIN, uid(15), {
      nickname: 'unver', gender: 'woman', birthDate: await yAgo(28), minAge: 20, maxAge: 40, genders: ['man'], status: 'active', verified: false,
    });
    // U_NOBD: no birth_date -> EXCLUDE
    await setupFullUser(db2, ADMIN, uid(16), {
      nickname: 'nobd', gender: 'woman', birthDate: null, minAge: 20, maxAge: 40, genders: ['man'],
    });
    // U_NOPREF: no preferences -> EXCLUDE
    await setupFullUser(db2, ADMIN, uid(17), {
      nickname: 'nopref', gender: 'woman', birthDate: await yAgo(28), genders: null,
    });
    // U_WRONG_G: man -> EXCLUDE
    await setupFullUser(db2, ADMIN, uid(18), {
      nickname: 'wrongg', gender: 'man', birthDate: await yAgo(28), minAge: 20, maxAge: 40, genders: ['man'],
    });
    // U_MUTUAL_G: woman who only wants woman -> EXCLUDE
    await setupFullUser(db2, ADMIN, uid(19), {
      nickname: 'mutg', gender: 'woman', birthDate: await yAgo(28), minAge: 20, maxAge: 40, genders: ['woman'],
    });
    // U_TOO_YOUNG: woman 24 -> EXCLUDE
    await setupFullUser(db2, ADMIN, uid(20), {
      nickname: 'young', gender: 'woman', birthDate: await yAgo(24), minAge: 20, maxAge: 40, genders: ['man'],
    });
    // U_MUTUAL_AGE: woman 28 who wants 31..40 (M1 is 30) -> EXCLUDE
    await setupFullUser(db2, ADMIN, uid(21), {
      nickname: 'mutage', gender: 'woman', birthDate: await yAgo(28), minAge: 31, maxAge: 40, genders: ['man'],
    });
    // U_BLOCKED_BY_ME: EXCLUDE
    const U_BLK1 = uid(22);
    await setupFullUser(db2, ADMIN, U_BLK1, {
      nickname: 'blk1', gender: 'woman', birthDate: await yAgo(28), minAge: 20, maxAge: 40, genders: ['man'],
    });
    await as(db2, M1, 'select public.block_user($1)', [U_BLK1]);
    // U_BLOCKED_ME: EXCLUDE
    const U_BLK2 = uid(23);
    await setupFullUser(db2, ADMIN, U_BLK2, {
      nickname: 'blk2', gender: 'woman', birthDate: await yAgo(28), minAge: 20, maxAge: 40, genders: ['man'],
    });
    await as(db2, U_BLK2, 'select public.block_user($1)', [M1]);
    // U_LIKED: I liked her -> EXCLUDE
    const U_LIKED = uid(24);
    await setupFullUser(db2, ADMIN, U_LIKED, {
      nickname: 'liked', gender: 'woman', birthDate: await yAgo(28), minAge: 20, maxAge: 40, genders: ['man'],
    });
    await as(db2, M1, "select public.swipe($1,'like')", [U_LIKED]);
    // U_LIKED_ME: she liked me -> INCLUDE!
    const U_LIKED_ME = uid(25);
    await setupFullUser(db2, ADMIN, U_LIKED_ME, {
      nickname: 'likedme', gender: 'woman', birthDate: await yAgo(28), minAge: 20, maxAge: 40, genders: ['man'],
    });
    await as(db2, U_LIKED_ME, "select public.swipe($1,'like')", [M1]);
    // U_PASS_RECENT: I passed 29 days ago -> EXCLUDE
    const U_PASS_REC = uid(26);
    await setupFullUser(db2, ADMIN, U_PASS_REC, {
      nickname: 'passrec', gender: 'woman', birthDate: await yAgo(28), minAge: 20, maxAge: 40, genders: ['man'],
    });
    await as(db2, M1, "select public.swipe($1,'pass')", [U_PASS_REC]);
    await sql(db2, "update public.swipes set created_at = now() - interval '29 days' where from_id=$1 and to_id=$2", [M1, U_PASS_REC]);
    // U_PASS_OLD: I passed 31 days ago -> INCLUDE!
    const U_PASS_OLD = uid(27);
    await setupFullUser(db2, ADMIN, U_PASS_OLD, {
      nickname: 'passold', gender: 'woman', birthDate: await yAgo(28), minAge: 20, maxAge: 40, genders: ['man'],
    });
    await as(db2, M1, "select public.swipe($1,'pass')", [U_PASS_OLD]);
    await sql(db2, "update public.swipes set created_at = now() - interval '31 days' where from_id=$1 and to_id=$2", [M1, U_PASS_OLD]);
    // U_MATCHED: active match (inserted directly without swipe to verify matches filter independently) -> EXCLUDE
    const U_MATCHED = uid(28);
    await setupFullUser(db2, ADMIN, U_MATCHED, {
      nickname: 'matched', gender: 'woman', birthDate: await yAgo(28), minAge: 20, maxAge: 40, genders: ['man'],
    });
    await sql(db2, 'insert into public.matches(user_a, user_b) values ($1, $2)', [M1, U_MATCHED]);
    // U_ENDED_MATCH: ended match (not blocked, not liked) -> INCLUDE!
    const U_ENDED = uid(29);
    await setupFullUser(db2, ADMIN, U_ENDED, {
      nickname: 'ended', gender: 'woman', birthDate: await yAgo(28), minAge: 20, maxAge: 40, genders: ['man'],
    });
    await sql(db2, 'insert into public.matches(user_a, user_b, ended_at) values ($1, $2, now())', [M1, U_ENDED]);

    const cands = (await as(db2, M1, 'select * from public.get_candidates()')).rows;
    assert.deepStrictEqual(
      cands.map((r) => r.id),
      [U_OK1, U_OK2, U_LIKED_ME, U_PASS_OLD, U_ENDED],
      'Exact candidate filter set'
    );
    // Exact columns returned (no birth_date)
    assert.deepStrictEqual(Object.keys(cands[0]), ['id', 'nickname', 'age', 'gender', 'region', 'bio']);
    assert.strictEqual(cands[0].age, 25);
    assert.strictEqual(cands[1].age, 35);

    // Limit works
    const candsLim = (await as(db2, M1, 'select * from public.get_candidates(2)')).rows;
    assert.strictEqual(candsLim.length, 2);
    const candsNamed = (await as(db2, M1, 'select * from public.get_candidates(lim => 3)')).rows;
    assert.strictEqual(candsNamed.length, 3);
    const candsZero = (await as(db2, M1, 'select * from public.get_candidates(0)')).rows;
    assert.strictEqual(candsZero.length, 0);
    await expectFail(as(db2, M1, 'select * from public.get_candidates(-1)'), 'negative lim');

    // Re-passing U_PASS_OLD resets 30-day cooldown
    await as(db2, M1, "select public.swipe($1,'pass')", [U_PASS_OLD]);
    const candsAfterRepass = (await as(db2, M1, 'select * from public.get_candidates()')).rows;
    assert.ok(!candsAfterRepass.some((r) => r.id === U_PASS_OLD), 're-passing refreshes 30d cooldown');

    // Ineligible callers get error on get_candidates
    await expectFail(as(db2, uid(13), 'select * from public.get_candidates()'), 'draft caller get_candidates');
    await expectFail(as(db2, uid(14), 'select * from public.get_candidates()'), 'suspended caller get_candidates');
    await expectFail(as(db2, uid(15), 'select * from public.get_candidates()'), 'unverified caller get_candidates');
  }
  console.log('7. get_candidates comprehensive filtering: PASS');

  // 8. swipe, match deduplication, messaging, blocking, RLS on swipes/matches/messages/blocks
  {
    await createUser(db, C);
    await as(db, C, "insert into public.profiles(id,nickname,gender,region) values ($1,'민수','man','seoul')", [C]);
    // C is draft/unverified -> cannot swipe, cannot be swiped
    await expectFail(as(db, C, "select public.swipe($1,'like')", [B]), 'ineligible caller swipe');
    await expectFail(as(db, A, "select public.swipe($1,'like')", [C]), 'ineligible target swipe');
    // Self swipe -> error
    await expectFail(as(db, A, "select public.swipe($1,'like')", [A]), 'self swipe');
    // Invalid action -> error
    await expectFail(as(db, A, "select public.swipe($1,'superlike')", [B]), 'invalid swipe action');
    // Direct write to swipes/matches/messages/blocks -> error
    await expectFail(as(db, A, "insert into public.swipes(from_id,to_id,action) values ($1,$2,'like')", [A, B]), 'direct insert swipes');
    await expectFail(as(db, A, 'insert into public.matches(user_a,user_b) values ($1,$2)', [A, B]), 'direct insert matches');
    await expectFail(as(db, A, 'insert into public.blocks(blocker_id,blocked_id) values ($1,$2)', [A, B]), 'direct insert blocks');

    // B likes A first (notice B > A in UUID order!) -> returns null
    const m0 = (await as(db, B, "select public.swipe($1,'like') as id", [A])).rows[0].id;
    assert.strictEqual(m0, null);
    // A cannot see B's swipe on A!
    assert.strictEqual((await as(db, A, 'select * from public.swipes')).rows.length, 0);
    assert.strictEqual((await as(db, B, 'select * from public.swipes')).rows.length, 1);

    // A passes B, then overwrites with like -> creates match!
    assert.strictEqual((await as(db, A, "select public.swipe($1,'pass') as id", [B])).rows[0].id, null);
    const matchId = (await as(db, A, "select public.swipe($1,'like') as id", [B])).rows[0].id;
    assert.ok(matchId, 'mutual like returns match id');

    // Repeated likes return SAME match id, only ONE match row exists
    const matchId2 = (await as(db, A, "select public.swipe($1,'like') as id", [B])).rows[0].id;
    const matchId3 = (await as(db, B, "select public.swipe($1,'like') as id", [A])).rows[0].id;
    assert.strictEqual(matchId2, matchId);
    assert.strictEqual(matchId3, matchId);
    assert.strictEqual(Number((await sql(db, 'select count(*) from public.matches')).rows[0].count), 1);

    // Verify user_a < user_b
    const matchRow = (await as(db, A, 'select * from public.matches')).rows[0];
    assert.strictEqual(matchRow.user_a, A);
    assert.strictEqual(matchRow.user_b, B);
    assert.strictEqual(matchRow.ended_at, null);
    // B sees match, C does not
    assert.strictEqual((await as(db, B, 'select * from public.matches')).rows.length, 1);
    assert.strictEqual((await as(db, C, 'select * from public.matches')).rows.length, 0);

    // Messaging
    await expectFail(as(db, A, "insert into public.messages(match_id,sender_id,body) values ($1,$2,'hack')", [matchId, A]), 'direct insert messages');
    await expectFail(as(db, C, "select public.send_message($1,'intrude')", [matchId]), 'non-participant send_message');
    await expectFail(as(db, A, "select public.send_message($1,'')", [matchId]), 'empty message');
    await expectFail(as(db, A, 'select public.send_message($1,$2)', [matchId, 'z'.repeat(2001)]), '2001-char message');

    const msg1 = (await as(db, A, "select public.send_message($1,'안녕!') as id", [matchId])).rows[0].id;
    const msg2 = (await as(db, B, 'select public.send_message($1,$2) as id', [matchId, 'z'.repeat(2000)])).rows[0].id;
    assert.ok(msg1 && msg2);

    // Both A and B see both messages; C sees 0
    assert.strictEqual((await as(db, A, 'select * from public.messages')).rows.length, 2);
    assert.strictEqual((await as(db, B, 'select * from public.messages')).rows.length, 2);
    assert.strictEqual((await as(db, C, 'select * from public.messages')).rows.length, 0);

    // Blocking ends match and blocks swiping & messaging
    await expectFail(as(db, A, 'select public.block_user($1)', [A]), 'self block');
    await as(db, A, 'select public.block_user($1)', [B]);
    // Idempotent second call
    await as(db, A, 'select public.block_user($1)', [B]);

    // A sees own block, B does NOT see A's block
    assert.strictEqual((await as(db, A, 'select * from public.blocks')).rows.length, 1);
    assert.strictEqual((await as(db, B, 'select * from public.blocks')).rows.length, 0);

    // Match ended_at is now set
    const endedMatch = (await as(db, A, 'select * from public.matches where id=$1', [matchId])).rows[0];
    assert.ok(endedMatch.ended_at !== null, 'block_user ends match');

    // Sending message & swiping now fail in both directions
    await expectFail(as(db, A, "select public.send_message($1,'after block')", [matchId]), 'send_message after block (blocker)');
    await expectFail(as(db, B, "select public.send_message($1,'after block')", [matchId]), 'send_message after block (blocked)');
    await expectFail(as(db, A, "select public.swipe($1,'like')", [B]), 'swipe after block (blocker)');
    await expectFail(as(db, B, "select public.swipe($1,'like')", [A]), 'swipe after block (blocked)');
  }
  console.log('8. swipe, match dedup, messaging, blocking & RLS: PASS');

  // 9. delete_my_account cascades everything for caller without touching others
  {
    await as(db, ADMIN, "select public.admin_set_status($1,'active',true)", [C]);
    await as(db, C, "select public.set_birth_date('1995-01-01')");
    await as(db, C, "insert into public.preferences(user_id,genders) values ($1,array['woman'])", [C]);
    // B and C match and message so we verify B-C survives A's deletion
    await as(db, B, "select public.swipe($1,'like')", [C]);
    const bcMatch = (await as(db, C, "select public.swipe($1,'like') as id", [B])).rows[0].id;
    await as(db, B, "select public.send_message($1,'hi C')", [bcMatch]);

    // Delete A's account
    await as(db, A, 'select public.delete_my_account()');

    // All of A's records are gone across every table
    const checks = [
      ['auth.users', 'id = $1'],
      ['public.profiles', 'id = $1'],
      ['public.member_status', 'user_id = $1'],
      ['private.user_private', 'user_id = $1'],
      ['private.admins', 'user_id = $1'],
      ['public.preferences', 'user_id = $1'],
      ['public.swipes', 'from_id = $1 or to_id = $1'],
      ['public.matches', 'user_a = $1 or user_b = $1'],
      ['public.messages', 'sender_id = $1'],
      ['public.blocks', 'blocker_id = $1 or blocked_id = $1'],
    ];
    for (const [tbl, cond] of checks) {
      const cnt = Number((await sql(db, `select count(*) from ${tbl} where ${cond}`, [A])).rows[0].count);
      assert.strictEqual(cnt, 0, `${tbl} still has rows for deleted user A`);
    }
    // Messages from A-B match (including B's message) were also cascaded via matches!
    const allMsgs = (await sql(db, 'select * from public.messages')).rows;
    assert.strictEqual(allMsgs.length, 1, 'Only B-C message remains');
    assert.strictEqual(allMsgs[0].match_id, bcMatch);
    assert.strictEqual(allMsgs[0].body, 'hi C');
  }
  console.log('9. delete_my_account full cascade isolation: PASS');

  // 10. Extra edge cases: null auth.uid() under authenticated role, infinite birth_date, block without ended_at, missing own pref/birth_date
  {
    const db3 = await makeDb(MIGRATION);
    const U1 = uid(101);
    const U2 = uid(102);
    await createUser(db3, ADMIN);
    await sql(db3, 'insert into private.admins(user_id) values ($1)', [ADMIN]);
    await setupFullUser(db3, ADMIN, U1, { nickname: 'u1', gender: 'man', genders: ['woman'] });
    await setupFullUser(db3, ADMIN, U2, { nickname: 'u2', gender: 'woman', genders: ['man'] });

    // authenticated role with empty JWT sub (auth.uid() = null)
    const asAuthNoSub = async (q, params = []) => {
      await db3.exec(`reset role; select set_config('request.jwt.claim.sub', '', false); set role authenticated;`);
      try { return await db3.query(q, params); }
      finally { await db3.exec(`reset role; select set_config('request.jwt.claim.sub', '', false);`); }
    };
    assert.strictEqual((await asAuthNoSub('select * from public.profiles')).rows.length, 0);
    await expectFail(asAuthNoSub("select public.set_birth_date('1990-01-01')"), 'auth null sub set_birth_date');
    await expectFail(asAuthNoSub("select public.admin_set_status($1,'active',true)", [U1]), 'auth null sub admin_set_status');
    await expectFail(asAuthNoSub('select * from public.get_candidates()'), 'auth null sub get_candidates');
    await expectFail(asAuthNoSub("select public.swipe($1,'like')", [U2]), 'auth null sub swipe');
    await expectFail(asAuthNoSub("select public.send_message($1,'hi')", [uid(999)]), 'auth null sub send_message');
    await expectFail(asAuthNoSub('select public.block_user($1)', [U2]), 'auth null sub block_user');
    await expectFail(asAuthNoSub('select public.delete_my_account()'), 'auth null sub delete_my_account');

    // Infinite dates rejected
    await expectFail(as(db3, U1, "select public.set_birth_date('infinity'::date)"), 'infinity birth_date');
    await expectFail(as(db3, U1, "select public.set_birth_date('-infinity'::date)"), '-infinity birth_date');

    // Direct block inserted by superuser (without ended_at) still blocks send_message
    await as(db3, U1, "select public.swipe($1,'like')", [U2]);
    const mid = (await as(db3, U2, "select public.swipe($1,'like') as id", [U1])).rows[0].id;
    await sql(db3, 'insert into public.blocks(blocker_id, blocked_id) values ($1, $2)', [U2, U1]);
    await expectFail(as(db3, U1, "select public.send_message($1,'blocked directly')", [mid]), 'send_message blocked without ended_at');

    // Caller eligible but missing own birth_date or preferences -> get_candidates returns 0 rows cleanly
    const U3 = uid(103);
    await setupFullUser(db3, ADMIN, U3, { nickname: 'u3', gender: 'man', birthDate: null, genders: ['woman'] });
    assert.strictEqual((await as(db3, U3, 'select * from public.get_candidates()')).rows.length, 0);

    // Candidate passed caller -> caller still sees candidate in get_candidates
    const U4 = uid(104);
    const U5 = uid(105);
    await setupFullUser(db3, ADMIN, U4, { nickname: 'u4', gender: 'man', genders: ['woman'] });
    await setupFullUser(db3, ADMIN, U5, { nickname: 'u5', gender: 'woman', genders: ['man'] });
    await as(db3, U5, "select public.swipe($1,'pass')", [U4]);
    const candsU4 = (await as(db3, U4, 'select * from public.get_candidates()')).rows;
    assert.ok(candsU4.some((r) => r.id === U5), 'candidate who passed me still shown to me');
  }
  console.log('10. Extra edge cases: PASS');

  console.log('ALL TESTS PASSED!');
}

run().catch((err) => {
  console.error('TEST FAILED:', err);
  process.exit(1);
});
