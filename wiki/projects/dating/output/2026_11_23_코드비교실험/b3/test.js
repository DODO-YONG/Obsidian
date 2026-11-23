const assert = require('assert');
const { makeDb, as, sql } = require('../harness/env');

const MIGRATION = __dirname + '/migration.sql';

const ADMIN = '00000000-0000-0000-0000-000000000001';
const A     = '00000000-0000-0000-0000-00000000000a';
const B     = '00000000-0000-0000-0000-00000000000b';
const C     = '00000000-0000-0000-0000-00000000000c';
const D     = '00000000-0000-0000-0000-00000000000d';
const E     = '00000000-0000-0000-0000-00000000000e';

async function expectError(promise, label) {
  let failed = false;
  try {
    await promise;
  } catch (err) {
    failed = true;
  }
  if (!failed) {
    throw new Error(`Expected error for: ${label}`);
  }
}

(async () => {
  const db = await makeDb(MIGRATION);

  // Seed users and admin
  for (const u of [ADMIN, A, B, C, D, E]) {
    await sql(db, 'insert into auth.users(id) values ($1)', [u]);
  }
  await sql(db, 'insert into private.admins(user_id) values ($1)', [ADMIN]);

  // 1. Anon security tests: cannot read any table or call any function
  for (const tbl of [
    'public.profiles',
    'public.member_status',
    'public.preferences',
    'public.swipes',
    'public.matches',
    'public.messages',
    'public.blocks',
    'private.user_private',
    'private.admins'
  ]) {
    await expectError(as(db, null, `select * from ${tbl}`), `anon select ${tbl}`);
  }
  await expectError(as(db, null, `select public.set_birth_date('1995-01-01')`), 'anon set_birth_date');
  await expectError(as(db, null, `select public.get_candidates()`), 'anon get_candidates');
  await expectError(as(db, null, `select public.swipe($1, 'like')`, [B]), 'anon swipe');
  await expectError(as(db, null, `select public.delete_my_account()`), 'anon delete_my_account');

  // 2. Profile creation & auto member_status trigger
  await expectError(
    as(db, A, `insert into public.profiles(id,nickname,gender,region) values ($1,'a','man','seoul')`, [A]),
    'nickname < 2 chars'
  );
  await expectError(
    as(db, A, `insert into public.profiles(id,nickname,gender,region) values ($1,'123456789012345678901','man','seoul')`, [A]),
    'nickname > 20 chars'
  );
  await expectError(
    as(db, A, `insert into public.profiles(id,nickname,gender,region) values ($1,'nickA','other','seoul')`, [A]),
    'invalid gender'
  );
  await expectError(
    as(db, A, `insert into public.profiles(id,nickname,gender,region,bio) values ($1,'nickA','man','seoul',$2)`, [A, 'x'.repeat(501)]),
    'bio > 500 chars'
  );
  await expectError(
    as(db, A, `insert into public.profiles(id,nickname,gender,region) values ($1,'nickB','woman','seoul')`, [B]),
    'insert another user profile'
  );

  await as(db, A, `insert into public.profiles(id,nickname,gender,region,bio) values ($1,'nickA','man','seoul','hello A')`, [A]);
  await as(db, B, `insert into public.profiles(id,nickname,gender,region,bio) values ($1,'nickB','woman','seoul','hello B')`, [B]);
  await as(db, C, `insert into public.profiles(id,nickname,gender,region,bio) values ($1,'nickC','woman','busan','hello C')`, [C]);
  await as(db, D, `insert into public.profiles(id,nickname,gender,region,bio) values ($1,'nickD','woman','incheon','hello D')`, [D]);
  await as(db, E, `insert into public.profiles(id,nickname,gender,region,bio) values ($1,'nickE','man','daegu','hello E')`, [E]);

  // Verify A can only read A's profile & member_status
  const aProfiles = (await as(db, A, 'select * from public.profiles')).rows;
  assert.strictEqual(aProfiles.length, 1);
  assert.strictEqual(aProfiles[0].id, A);

  const aStatus = (await as(db, A, 'select * from public.member_status')).rows;
  assert.strictEqual(aStatus.length, 1);
  assert.strictEqual(aStatus[0].user_id, A);
  assert.strictEqual(aStatus[0].status, 'draft');
  assert.strictEqual(aStatus[0].photo_verified, false);

  // User cannot update own member_status
  await expectError(
    as(db, A, `update public.member_status set status = 'active', photo_verified = true where user_id = $1`, [A]),
    'user update own member_status'
  );

  // 3. set_birth_date & private schema isolation
  await expectError(as(db, A, `select * from private.user_private`), 'read private.user_private');
  await expectError(as(db, A, `select * from private.admins`), 'read private.admins');
  await expectError(as(db, A, `select public.set_birth_date((current_date - interval '18 years')::date)`), 'under 19 birth_date');

  // Exactly 19 years old today should succeed
  await as(db, A, `select public.set_birth_date((current_date - interval '19 years')::date)`);
  // Update birth_date to 26 years old
  await as(db, A, `select public.set_birth_date((current_date - interval '26 years')::date)`);
  await as(db, B, `select public.set_birth_date((current_date - interval '24 years')::date)`);
  await as(db, C, `select public.set_birth_date((current_date - interval '25 years')::date)`);
  await as(db, D, `select public.set_birth_date((current_date - interval '35 years')::date)`);
  // Note: E has no birth_date yet

  // 4. preferences & RLS
  await expectError(
    as(db, A, `insert into public.preferences(user_id,min_age,max_age,genders) values ($1,18,30,array['woman'])`, [A]),
    'min_age < 19'
  );
  await expectError(
    as(db, A, `insert into public.preferences(user_id,min_age,max_age,genders) values ($1,30,25,array['woman'])`, [A]),
    'min_age > max_age'
  );
  await expectError(
    as(db, A, `insert into public.preferences(user_id,min_age,max_age,genders) values ($1,20,100,array['woman'])`, [A]),
    'max_age > 99'
  );
  await expectError(
    as(db, A, `insert into public.preferences(user_id,min_age,max_age,genders) values ($1,20,30,array['man'])`, [B]),
    'insert preferences for another user'
  );

  await as(db, A, `insert into public.preferences(user_id,min_age,max_age,genders) values ($1,20,30,array['woman'])`, [A]);
  await as(db, B, `insert into public.preferences(user_id,min_age,max_age,genders) values ($1,20,30,array['man'])`, [B]);
  await as(db, C, `insert into public.preferences(user_id,min_age,max_age,genders) values ($1,20,30,array['man'])`, [C]);
  await as(db, D, `insert into public.preferences(user_id,min_age,max_age,genders) values ($1,20,40,array['man'])`, [D]); // D is 35 (outside A's 20..30)
  await as(db, E, `insert into public.preferences(user_id,min_age,max_age,genders) values ($1,20,30,array['woman'])`, [E]);

  const aPrefs = (await as(db, A, 'select * from public.preferences')).rows;
  assert.strictEqual(aPrefs.length, 1);
  assert.strictEqual(aPrefs[0].user_id, A);

  // 5. admin_set_status & eligibility
  await expectError(
    as(db, A, `select public.admin_set_status($1, 'active', true)`, [A]),
    'non-admin calling admin_set_status'
  );
  await expectError(
    as(db, A, `select public.get_candidates()`),
    'unqualified caller get_candidates'
  );

  await as(db, ADMIN, `select public.admin_set_status($1, 'active', true)`, [A]);
  await as(db, ADMIN, `select public.admin_set_status($1, 'active', true)`, [B]);
  await as(db, ADMIN, `select public.admin_set_status($1, 'active', true)`, [C]);
  await as(db, ADMIN, `select public.admin_set_status($1, 'active', true)`, [D]);
  await as(db, ADMIN, `select public.admin_set_status($1, 'active', true)`, [E]);

  // 6. get_candidates
  // For A (man, 26, wants woman 20..30):
  // - B (woman, 24, wants man 20..30): MATCH
  // - C (woman, 25, wants man 20..30): MATCH
  // - D (woman, 35, wants man 20..40): excluded (D's age 35 > A's max_age 30)
  // - E (man, no birth_date): excluded
  let cands = (await as(db, A, `select * from public.get_candidates()`)).rows;
  assert.deepStrictEqual(cands.map(r => r.id).sort(), [B, C].sort());
  const bCand = cands.find(r => r.id === B);
  assert.strictEqual(bCand.age, 24);
  assert.strictEqual(bCand.nickname, 'nickB');

  // For B (woman, 24, wants man 20..30):
  // - A (man, 26): MATCH
  // - E (man, no birth_date): excluded because no birth_date
  let bCands = (await as(db, B, `select * from public.get_candidates()`)).rows;
  assert.deepStrictEqual(bCands.map(r => r.id), [A]);

  // 7. swipe & pass 30-day rule
  await expectError(as(db, A, `select public.swipe($1, 'like')`, [A]), 'swipe self');
  await expectError(as(db, A, `insert into public.swipes(from_id,to_id,action) values ($1,$2,'like')`, [A, B]), 'direct insert swipes');

  // A passes C
  let resSwipe = (await as(db, A, `select public.swipe($1, 'pass') as mid`, [C])).rows[0].mid;
  assert.strictEqual(resSwipe, null);

  // C should now be excluded from A's candidates (passed within 30 days)
  cands = (await as(db, A, `select * from public.get_candidates()`)).rows;
  assert.deepStrictEqual(cands.map(r => r.id), [B]);

  // Simulate pass was 31 days ago
  await sql(db, `update public.swipes set created_at = now() - interval '31 days' where from_id = $1 and to_id = $2`, [A, C]);
  cands = (await as(db, A, `select * from public.get_candidates()`)).rows;
  assert.deepStrictEqual(cands.map(r => r.id).sort(), [B, C].sort());

  // A likes B -> no match yet
  resSwipe = (await as(db, A, `select public.swipe($1, 'like') as mid`, [B])).rows[0].mid;
  assert.strictEqual(resSwipe, null);

  // B cannot read A's swipe directly
  assert.strictEqual((await as(db, B, `select * from public.swipes`)).rows.length, 0);
  assert.strictEqual((await as(db, A, `select * from public.swipes`)).rows.length, 2);

  // B is now excluded from A's get_candidates (already liked)
  cands = (await as(db, A, `select * from public.get_candidates()`)).rows;
  assert.deepStrictEqual(cands.map(r => r.id), [C]);

  // B likes A -> match created!
  const matchId = (await as(db, B, `select public.swipe($1, 'like') as mid`, [A])).rows[0].mid;
  assert.ok(matchId, 'matchId should be returned');

  // Re-swiping like should not create duplicate match
  const matchId2 = (await as(db, A, `select public.swipe($1, 'like') as mid`, [B])).rows[0].mid;
  assert.strictEqual(matchId2, matchId);

  // A is excluded from B's candidates (already matched & liked)
  bCands = (await as(db, B, `select * from public.get_candidates()`)).rows;
  assert.strictEqual(bCands.length, 0);

  // Match visibility: A and B can see, C cannot
  assert.strictEqual((await as(db, A, `select * from public.matches`)).rows.length, 1);
  assert.strictEqual((await as(db, B, `select * from public.matches`)).rows.length, 1);
  assert.strictEqual((await as(db, C, `select * from public.matches`)).rows.length, 0);

  // 8. send_message
  await expectError(as(db, C, `select public.send_message($1, 'hi')`, [matchId]), 'non-participant send_message');
  await expectError(as(db, A, `select public.send_message($1, '')`, [matchId]), 'empty message body');
  await expectError(as(db, A, `insert into public.messages(id,match_id,sender_id,body) values (gen_random_uuid(),$1,$2,'hi')`, [matchId, A]), 'direct insert messages');

  const msgId = (await as(db, A, `select public.send_message($1, 'Hello B!') as id`, [matchId])).rows[0].id;
  assert.ok(msgId);

  assert.strictEqual((await as(db, A, `select * from public.messages`)).rows.length, 1);
  assert.strictEqual((await as(db, B, `select * from public.messages`)).rows.length, 1);
  assert.strictEqual((await as(db, C, `select * from public.messages`)).rows.length, 0);

  // 9. block_user
  await expectError(as(db, A, `insert into public.blocks(blocker_id,blocked_id) values ($1,$2)`, [A, B]), 'direct insert blocks');
  await as(db, A, `select public.block_user($1)`, [B]);

  // Only blocker A can see the block, not B
  assert.strictEqual((await as(db, A, `select * from public.blocks`)).rows.length, 1);
  assert.strictEqual((await as(db, B, `select * from public.blocks`)).rows.length, 0);

  // Match between A and B should now have ended_at set
  const matchRow = (await as(db, A, `select * from public.matches where id = $1`, [matchId])).rows[0];
  assert.ok(matchRow.ended_at, 'ended_at should be set after block_user');

  // Cannot send message or swipe after block
  await expectError(as(db, A, `select public.send_message($1, 'after block')`, [matchId]), 'send_message after block');
  await expectError(as(db, B, `select public.send_message($1, 'after block')`, [matchId]), 'send_message by blocked user');
  await expectError(as(db, A, `select public.swipe($1, 'like')`, [B]), 'swipe after block');
  await expectError(as(db, B, `select public.swipe($1, 'like')`, [A]), 'swipe by blocked user');

  // 10. delete_my_account
  await as(db, A, `select public.delete_my_account()`);
  const remainingA = (await sql(db, `select * from auth.users where id = $1`, [A])).rows;
  assert.strictEqual(remainingA.length, 0);
  assert.strictEqual((await sql(db, `select * from public.profiles where id = $1`, [A])).rows.length, 0);
  assert.strictEqual((await sql(db, `select * from public.member_status where user_id = $1`, [A])).rows.length, 0);
  assert.strictEqual((await sql(db, `select * from private.user_private where user_id = $1`, [A])).rows.length, 0);
  assert.strictEqual((await sql(db, `select * from public.matches where id = $1`, [matchId])).rows.length, 0);
  assert.strictEqual((await sql(db, `select * from public.messages where id = $1`, [msgId])).rows.length, 0);

  console.log('ALL TESTS PASSED!');
})();
