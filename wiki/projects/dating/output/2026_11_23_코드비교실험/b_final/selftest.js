const assert = require('assert');
const path = require('path');
const { makeDb, as, sql } = require('../harness/env');

const MIGRATION = path.join(__dirname, 'migration.sql');

const U = {
  A: '00000000-0000-0000-0000-00000000000a',
  B: '00000000-0000-0000-0000-00000000000b',
  C: '00000000-0000-0000-0000-00000000000c',
  D: '00000000-0000-0000-0000-00000000000d',
  E: '00000000-0000-0000-0000-00000000000e',
  ADMIN: '00000000-0000-0000-0000-0000000000ff',
};

async function mustFail(promise, label) {
  let failed = false;
  try {
    await promise;
  } catch (e) {
    failed = true;
  }
  assert.strictEqual(failed, true, `Expected failure: ${label}`);
}

async function setupUser(db, id, { nick, gender, region = 'seoul', bio = 'hi', birth = '1995-01-01', minAge = 19, maxAge = 40, genders = ['man', 'woman'], activate = true }) {
  await sql(db, 'insert into auth.users(id) values ($1)', [id]);
  await as(db, id, 'insert into public.profiles(id, nickname, gender, region, bio) values ($1,$2,$3,$4,$5)', [id, nick, gender, region, bio]);
  if (birth) {
    await as(db, id, 'select public.set_birth_date($1)', [birth]);
  }
  if (genders !== null) {
    await as(db, id, 'insert into public.preferences(user_id, min_age, max_age, genders) values ($1,$2,$3,$4)', [id, minAge, maxAge, genders]);
  }
  if (activate) {
    await as(db, U.ADMIN, "select public.admin_set_status($1, 'active', true)", [id]);
  }
}

async function run() {
  let passed = 0;
  async function test(name, fn) {
    const db = await makeDb(MIGRATION);
    await sql(db, 'insert into auth.users(id) values ($1)', [U.ADMIN]);
    await sql(db, 'insert into private.admins(user_id) values ($1)', [U.ADMIN]);
    try {
      await fn(db);
      passed++;
      console.log(`PASS: ${name}`);
    } catch (e) {
      console.error(`FAIL: ${name}`);
      throw e;
    } finally {
      await db.close();
    }
  }

  // 1. Trigger creates member_status & profile constraints
  await test('profiles constraints & auto member_status trigger', async (db) => {
    await sql(db, 'insert into auth.users(id) values ($1)', [U.A]);
    // nickname too short / too long
    await mustFail(as(db, U.A, "insert into public.profiles(id,nickname,gender,region) values ($1,'a','man','seoul')", [U.A]), 'nick 1 char');
    await mustFail(as(db, U.A, "insert into public.profiles(id,nickname,gender,region) values ($1,$2,'man','seoul')", [U.A, 'x'.repeat(21)]), 'nick 21 chars');
    // invalid gender
    await mustFail(as(db, U.A, "insert into public.profiles(id,nickname,gender,region) values ($1,'nickA','other','seoul')", [U.A]), 'invalid gender');
    // bio > 500
    await mustFail(as(db, U.A, "insert into public.profiles(id,nickname,gender,region,bio) values ($1,'nickA','man','seoul',$2)", [U.A, 'b'.repeat(501)]), 'bio > 500');
    // valid insert (Korean 2 chars)
    await as(db, U.A, "insert into public.profiles(id,nickname,gender,region) values ($1,'철수','man','seoul')", [U.A]);
    const ms = (await as(db, U.A, 'select * from public.member_status')).rows;
    assert.strictEqual(ms.length, 1);
    assert.strictEqual(ms[0].user_id, U.A);
    assert.strictEqual(ms[0].status, 'draft');
    assert.strictEqual(ms[0].photo_verified, false);
    // update own profile
    await as(db, U.A, "update public.profiles set bio = 'updated' where id = $1", [U.A]);
    const p = (await as(db, U.A, 'select bio from public.profiles')).rows;
    assert.strictEqual(p[0].bio, 'updated');
    // cannot delete own profile directly
    await mustFail(as(db, U.A, 'delete from public.profiles where id = $1', [U.A]), 'direct delete profile');
  });

  // 2. anon cannot read any table or call any function
  await test('anon blocked from all tables and all functions', async (db) => {
    await setupUser(db, U.A, { nick: 'nickA', gender: 'man' });
    const tables = [
      'public.profiles', 'public.member_status', 'public.preferences',
      'public.swipes', 'public.matches', 'public.messages', 'public.blocks',
      'private.user_private', 'private.admins',
    ];
    for (const t of tables) {
      await mustFail(as(db, null, `select * from ${t}`), `anon select ${t}`);
    }
    await mustFail(as(db, null, "select public.set_birth_date('1995-01-01')"), 'anon set_birth_date');
    await mustFail(as(db, null, "select public.admin_set_status($1,'active',true)", [U.A]), 'anon admin_set_status');
    await mustFail(as(db, null, 'select * from public.get_candidates()'), 'anon get_candidates');
    await mustFail(as(db, null, "select public.swipe($1,'like')", [U.A]), 'anon swipe');
    await mustFail(as(db, null, "select public.send_message($1,'hi')", [U.A]), 'anon send_message');
    await mustFail(as(db, null, 'select public.block_user($1)', [U.A]), 'anon block_user');
    await mustFail(as(db, null, 'select public.delete_my_account()'), 'anon delete_my_account');
  });

  // 3. RLS isolation & direct write restrictions for authenticated
  await test('RLS isolation and direct write prevention', async (db) => {
    await setupUser(db, U.A, { nick: 'nickA', gender: 'man' });
    await setupUser(db, U.B, { nick: 'nickB', gender: 'woman' });

    // A cannot see B's profile, member_status, preferences
    assert.strictEqual((await as(db, U.A, 'select * from public.profiles')).rows.length, 1);
    assert.strictEqual((await as(db, U.A, 'select * from public.profiles where id = $1', [U.B])).rows.length, 0);
    assert.strictEqual((await as(db, U.A, 'select * from public.member_status where user_id = $1', [U.B])).rows.length, 0);
    assert.strictEqual((await as(db, U.A, 'select * from public.preferences where user_id = $1', [U.B])).rows.length, 0);

    // A cannot insert/update B's profile or preferences
    await mustFail(as(db, U.A, "insert into public.profiles(id,nickname,gender,region) values ($1,'hack','man','seoul')", [U.C]), 'insert other profile');
    await as(db, U.A, "update public.profiles set nickname='hacked' where id = $1", [U.B]);
    assert.strictEqual((await sql(db, 'select nickname from public.profiles where id = $1', [U.B])).rows[0].nickname, 'nickB');
    await mustFail(as(db, U.A, "update public.profiles set id = $1 where id = $2", [U.C, U.A]), 'hijack profile id');

    // A cannot modify member_status directly or via admin_set_status
    await mustFail(as(db, U.A, "update public.member_status set status='active' where user_id=$1", [U.A]), 'direct update member_status');
    await mustFail(as(db, U.A, "insert into public.member_status(user_id) values ($1)", [U.A]), 'direct insert member_status');
    await mustFail(as(db, U.A, "delete from public.member_status where user_id=$1", [U.A]), 'direct delete member_status');
    await mustFail(as(db, U.A, "select public.admin_set_status($1,'suspended',false)", [U.B]), 'non-admin admin_set_status');

    // A cannot read private schema
    await mustFail(as(db, U.A, 'select * from private.user_private'), 'read user_private');
    await mustFail(as(db, U.A, 'select * from private.admins'), 'read admins');

    // Direct writes to swipes, matches, messages, blocks fail
    await mustFail(as(db, U.A, "insert into public.swipes(from_id,to_id,action) values ($1,$2,'like')", [U.A, U.B]), 'direct insert swipes');
    await mustFail(as(db, U.A, "insert into public.matches(user_a,user_b) values ($1,$2)", [U.A, U.B]), 'direct insert matches');
    await mustFail(as(db, U.A, "insert into public.blocks(blocker_id,blocked_id) values ($1,$2)", [U.A, U.B]), 'direct insert blocks');

    // Preferences constraints
    await mustFail(as(db, U.A, 'update public.preferences set min_age = 18 where user_id = $1', [U.A]), 'min_age 18');
    await mustFail(as(db, U.A, 'update public.preferences set min_age = 30, max_age = 25 where user_id = $1', [U.A]), 'min > max');
    await mustFail(as(db, U.A, 'update public.preferences set max_age = 100 where user_id = $1', [U.A]), 'max_age 100');
  });

  // 4. set_birth_date & age boundaries
  await test('set_birth_date validation and upsert', async (db) => {
    await sql(db, 'insert into auth.users(id) values ($1)', [U.A]);
    // exactly 19 today (relative to postgres current_date)
    const { rows: [d] } = await sql(db, "select (current_date - interval '19 years')::date as ok, (current_date - interval '19 years' + interval '1 day')::date as young");
    await mustFail(as(db, U.A, 'select public.set_birth_date($1)', [d.young]), 'under 19 by 1 day');
    await mustFail(as(db, U.A, 'select public.set_birth_date(null)'), 'null birth_date');
    await as(db, U.A, 'select public.set_birth_date($1)', [d.ok]);
    // update existing birth_date
    await as(db, U.A, "select public.set_birth_date('1990-05-05')");
    const saved = (await sql(db, 'select birth_date::text as bd from private.user_private where user_id = $1', [U.A])).rows[0];
    assert.strictEqual(saved.bd, '1990-05-05');
  });

  // 5. get_candidates comprehensive filtering
  await test('get_candidates all conditions', async (db) => {
    // A: man, age ~30, wants woman 20-35
    await setupUser(db, U.A, { nick: 'userA', gender: 'man', birth: '1996-01-01', minAge: 20, maxAge: 35, genders: ['woman'] });
    // B: woman, age ~28, wants man 25-35 -> MATCHING CANDIDATE
    await setupUser(db, U.B, { nick: 'userB', gender: 'woman', birth: '1998-01-01', minAge: 25, maxAge: 35, genders: ['man'] });
    // C: woman, age ~28, wants woman -> mutual gender fails
    await setupUser(db, U.C, { nick: 'userC', gender: 'woman', birth: '1998-01-01', minAge: 20, maxAge: 40, genders: ['woman'] });
    // D: woman, age ~28, wants man 40-50 -> mutual age fails (A is ~30)
    await setupUser(db, U.D, { nick: 'userD', gender: 'woman', birth: '1998-01-01', minAge: 40, maxAge: 50, genders: ['man'] });
    // E: woman, no birth_date -> excluded
    await setupUser(db, U.E, { nick: 'userE', gender: 'woman', birth: null, minAge: 20, maxAge: 40, genders: ['man'] });

    // A sees only B
    let cands = (await as(db, U.A, 'select * from public.get_candidates()')).rows;
    assert.strictEqual(cands.length, 1);
    assert.strictEqual(cands[0].id, U.B);
    assert.strictEqual(cands[0].nickname, 'userB');
    assert.strictEqual(typeof cands[0].age, 'number');
    assert.strictEqual(cands[0].gender, 'woman');

    // Unqualified caller gets error
    await as(db, U.ADMIN, "select public.admin_set_status($1, 'active', false)", [U.A]);
    await mustFail(as(db, U.A, 'select * from public.get_candidates()'), 'unverified caller');
    await as(db, U.ADMIN, "select public.admin_set_status($1, 'suspended', true)", [U.A]);
    await mustFail(as(db, U.A, 'select * from public.get_candidates()'), 'suspended caller');
    await as(db, U.ADMIN, "select public.admin_set_status($1, 'active', true)", [U.A]);

    // Unqualified candidate excluded
    await as(db, U.ADMIN, "select public.admin_set_status($1, 'draft', true)", [U.B]);
    assert.strictEqual((await as(db, U.A, 'select * from public.get_candidates()')).rows.length, 0);
    await as(db, U.ADMIN, "select public.admin_set_status($1, 'active', true)", [U.B]);

    // Pass excludes for 30 days, reappears after 30 days
    await as(db, U.A, "select public.swipe($1, 'pass')", [U.B]);
    assert.strictEqual((await as(db, U.A, 'select * from public.get_candidates()')).rows.length, 0);
    await sql(db, "update public.swipes set created_at = now() - interval '29 days' where from_id = $1 and to_id = $2", [U.A, U.B]);
    assert.strictEqual((await as(db, U.A, 'select * from public.get_candidates()')).rows.length, 0);
    await sql(db, "update public.swipes set created_at = now() - interval '31 days' where from_id = $1 and to_id = $2", [U.A, U.B]);
    assert.strictEqual((await as(db, U.A, 'select * from public.get_candidates()')).rows.length, 1);

    // Re-pass resets created_at and excludes again
    await as(db, U.A, "select public.swipe($1, 'pass')", [U.B]);
    assert.strictEqual((await as(db, U.A, 'select * from public.get_candidates()')).rows.length, 0);

    // Like excludes permanently (even > 30 days)
    await as(db, U.A, "select public.swipe($1, 'like')", [U.B]);
    await sql(db, "update public.swipes set created_at = now() - interval '60 days' where from_id = $1 and to_id = $2", [U.A, U.B]);
    assert.strictEqual((await as(db, U.A, 'select * from public.get_candidates()')).rows.length, 0);

    // B still sees A (A liked B, B hasn't swiped A)
    assert.strictEqual((await as(db, U.B, 'select * from public.get_candidates()')).rows.length, 1);

    // lim parameter
    assert.strictEqual((await as(db, U.B, 'select * from public.get_candidates(0)')).rows.length, 0);
    assert.strictEqual((await as(db, U.B, 'select * from public.get_candidates(1)')).rows.length, 1);
  });

  // 6. swipe, match uniqueness, send_message, block_user
  await test('swipe -> match -> message -> block lifecycle', async (db) => {
    await setupUser(db, U.A, { nick: 'userA', gender: 'man' });
    await setupUser(db, U.B, { nick: 'userB', gender: 'woman' });
    await setupUser(db, U.C, { nick: 'userC', gender: 'woman' });

    // self swipe fails
    await mustFail(as(db, U.A, "select public.swipe($1, 'like')", [U.A]), 'self swipe');
    // invalid action fails
    await mustFail(as(db, U.A, "select public.swipe($1, 'super')", [U.B]), 'invalid action');

    // A likes B -> null
    const r1 = (await as(db, U.A, "select public.swipe($1, 'like') as mid", [U.B])).rows[0].mid;
    assert.strictEqual(r1, null);
    // B cannot see A's swipe
    assert.strictEqual((await as(db, U.B, 'select * from public.swipes')).rows.length, 0);
    // A sees own swipe
    assert.strictEqual((await as(db, U.A, 'select * from public.swipes')).rows.length, 1);

    // B likes A -> match created!
    const mid = (await as(db, U.B, "select public.swipe($1, 'like') as mid", [U.A])).rows[0].mid;
    assert.ok(mid);

    // Re-liking returns the SAME match id and keeps only 1 match row
    const mid2 = (await as(db, U.A, "select public.swipe($1, 'like') as mid", [U.B])).rows[0].mid;
    assert.strictEqual(mid2, mid);
    assert.strictEqual((await sql(db, 'select count(*)::int as c from public.matches')).rows[0].c, 1);

    // Both A and B see match; C does not
    assert.strictEqual((await as(db, U.A, 'select * from public.matches')).rows.length, 1);
    assert.strictEqual((await as(db, U.B, 'select * from public.matches')).rows.length, 1);
    assert.strictEqual((await as(db, U.C, 'select * from public.matches')).rows.length, 0);

    // Messaging
    const m1 = (await as(db, U.A, "select public.send_message($1, 'hello') as id", [mid])).rows[0].id;
    assert.ok(m1);
    const m2 = (await as(db, U.B, "select public.send_message($1, 'hi!') as id", [mid])).rows[0].id;
    assert.ok(m2);
    // C cannot send or read messages
    await mustFail(as(db, U.C, "select public.send_message($1, 'intrude')", [mid]), 'non-participant send_message');
    assert.strictEqual((await as(db, U.C, 'select * from public.messages')).rows.length, 0);
    assert.strictEqual((await as(db, U.A, 'select * from public.messages')).rows.length, 2);
    assert.strictEqual((await as(db, U.B, 'select * from public.messages')).rows.length, 2);
    // Invalid body length
    await mustFail(as(db, U.A, "select public.send_message($1, '')", [mid]), 'empty message');
    await mustFail(as(db, U.A, 'select public.send_message($1, $2)', [mid, 'x'.repeat(2001)]), 'too long message');
    // Direct insert into messages fails
    await mustFail(as(db, U.A, "insert into public.messages(match_id, sender_id, body) values ($1,$2,'hack')", [mid, U.A]), 'direct insert message');

    // A blocks B -> ends match, blocks messaging & swiping & candidates
    await as(db, U.A, 'select public.block_user($1)', [U.B]);
    const matchRow = (await as(db, U.A, 'select ended_at from public.matches where id = $1', [mid])).rows[0];
    assert.ok(matchRow.ended_at !== null);
    // Only A sees the block, B does not
    assert.strictEqual((await as(db, U.A, 'select * from public.blocks')).rows.length, 1);
    assert.strictEqual((await as(db, U.B, 'select * from public.blocks')).rows.length, 0);
    // Neither A nor B can send message or swipe each other
    await mustFail(as(db, U.A, "select public.send_message($1, 'after block')", [mid]), 'A send after block');
    await mustFail(as(db, U.B, "select public.send_message($1, 'after block')", [mid]), 'B send after block');
    await mustFail(as(db, U.A, "select public.swipe($1, 'like')", [U.B]), 'A swipe blocked B');
    await mustFail(as(db, U.B, "select public.swipe($1, 'like')", [U.A]), 'B swipe blocker A');

    // Active match excludes from get_candidates (test with A and C)
    await as(db, U.A, "select public.swipe($1, 'like')", [U.C]);
    await as(db, U.C, "select public.swipe($1, 'like')", [U.A]);
    // Delete swipes as superuser to isolate the active-match exclusion check
    await sql(db, 'delete from public.swipes');
    assert.strictEqual((await as(db, U.A, 'select * from public.get_candidates()')).rows.length, 0);
    // C should not see A (matched), only B (unmatched, unblocked)
    const cCands = (await as(db, U.C, 'select * from public.get_candidates()')).rows;
    assert.strictEqual(cCands.length, 1);
    assert.strictEqual(cCands[0].id, U.B);

    // Reverse block check: B blocked by A, so B also must not see A even if match weren't ended
    assert.strictEqual((await as(db, U.B, 'select * from public.get_candidates()')).rows.some(r => r.id === U.A), false);

    // Direct update/delete on swipes, matches, messages, blocks fail
    await mustFail(as(db, U.A, "update public.matches set ended_at = null where id = $1", [mid]), 'direct update matches');
    await mustFail(as(db, U.A, "delete from public.matches where id = $1", [mid]), 'direct delete matches');
    await mustFail(as(db, U.A, "update public.messages set body = 'edit' where id = $1", [m1]), 'direct update messages');
    await mustFail(as(db, U.A, "delete from public.messages where id = $1", [m1]), 'direct delete messages');
    await mustFail(as(db, U.A, "delete from public.blocks where blocker_id = $1", [U.A]), 'direct delete blocks');
    await mustFail(as(db, U.A, "delete from public.swipes where from_id = $1", [U.A]), 'direct delete swipes');

    // Named argument calls & exact age calculation
    const { rows: [bday] } = await sql(db, "select (current_date - interval '25 years')::date as b25, (current_date - interval '25 years' + interval '1 day')::date as b24");
    await as(db, U.B, 'select public.set_birth_date(d => $1)', [bday.b25]);
    assert.strictEqual((await as(db, U.C, 'select age from public.get_candidates(lim => 5) where id = $1', [U.B])).rows[0].age, 25);
    await as(db, U.B, 'select public.set_birth_date(d => $1)', [bday.b24]);
    assert.strictEqual((await as(db, U.C, 'select age from public.get_candidates(lim => 5) where id = $1', [U.B])).rows[0].age, 24);
  });

  // 7. delete_my_account cascades everything
  await test('delete_my_account cascades all user data', async (db) => {
    await setupUser(db, U.A, { nick: 'userA', gender: 'man' });
    await setupUser(db, U.B, { nick: 'userB', gender: 'woman' });
    await setupUser(db, U.C, { nick: 'userC', gender: 'woman' });

    await as(db, U.A, "select public.swipe($1, 'like')", [U.B]);
    const mid = (await as(db, U.B, "select public.swipe($1, 'like') as id", [U.A])).rows[0].id;
    await as(db, U.A, "select public.send_message($1, 'bye')", [mid]);
    await as(db, U.B, "select public.send_message($1, 'wait')", [mid]);
    await as(db, U.A, 'select public.block_user($1)', [U.C]);
    await as(db, U.C, 'select public.block_user($1)', [U.A]);

    await as(db, U.A, 'select public.delete_my_account()');

    // Verify all A data is gone
    const checks = [
      ['auth.users', 'id'],
      ['public.profiles', 'id'],
      ['public.member_status', 'user_id'],
      ['private.user_private', 'user_id'],
      ['public.preferences', 'user_id'],
      ['public.swipes', 'from_id'],
      ['public.swipes', 'to_id'],
      ['public.matches', 'user_a'],
      ['public.matches', 'user_b'],
      ['public.messages', 'sender_id'],
      ['public.blocks', 'blocker_id'],
      ['public.blocks', 'blocked_id'],
    ];
    for (const [tbl, col] of checks) {
      const c = (await sql(db, `select count(*)::int as c from ${tbl} where ${col} = $1`, [U.A])).rows[0].c;
      assert.strictEqual(c, 0, `${tbl}.${col} still has A`);
    }
    // Messages from B in the deleted match also cascaded!
    assert.strictEqual((await sql(db, 'select count(*)::int as c from public.messages')).rows[0].c, 0);
    // B and C still exist
    assert.strictEqual((await sql(db, 'select count(*)::int as c from public.profiles')).rows[0].c, 2);
  });

  // 8. Privilege metadata verification (security definer, search_path, grants)
  await test('security metadata check: search_path, definer, grants', async (db) => {
    const fns = (await sql(db, `
      select n.nspname, p.proname, p.prosecdef, p.proconfig
      from pg_proc p
      join pg_namespace n on n.oid = p.pronamespace
      where n.nspname in ('public', 'private')
    `)).rows;
    assert.strictEqual(fns.length, 8); // 7 public + 1 private trigger
    for (const fn of fns) {
      assert.strictEqual(fn.prosecdef, true, `${fn.nspname}.${fn.proname} not security definer`);
      assert.ok(fn.proconfig && fn.proconfig.some(c => c.startsWith('search_path=')), `${fn.nspname}.${fn.proname} missing search_path: ${JSON.stringify(fn.proconfig)}`);
    }
    // Check anon has zero function/table privileges
    const privs = (await sql(db, `
      select table_schema, table_name, privilege_type
      from information_schema.role_table_grants
      where grantee in ('anon', 'PUBLIC')
        and table_schema in ('public', 'private')
    `)).rows;
    assert.strictEqual(privs.length, 0, `Unexpected anon/PUBLIC table grants: ${JSON.stringify(privs)}`);

    const fnPrivs = (await sql(db, `
      select routine_schema, routine_name
      from information_schema.role_routine_grants
      where grantee in ('anon', 'PUBLIC')
        and routine_schema in ('public', 'private')
    `)).rows;
    assert.strictEqual(fnPrivs.length, 0, `Unexpected anon/PUBLIC routine grants: ${JSON.stringify(fnPrivs)}`);
  });

  console.log(`\nALL ${passed} TESTS PASSED!`);
}

run().catch((e) => {
  console.error(e);
  process.exit(1);
});
