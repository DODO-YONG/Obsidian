// 예시: node harness/selftest-example.js <migration.sql>
const { makeDb, as, sql } = require('./env');
(async () => {
  const db = await makeDb(process.argv[2]);
  const A = '00000000-0000-0000-0000-00000000000a';
  await sql(db, 'insert into auth.users(id) values ($1)', [A]);
  await as(db, A, "insert into public.profiles(id,nickname,gender,region) values ($1,'nickA','man','seoul')", [A]);
  console.log((await as(db, A, 'select * from public.member_status')).rows);
})();
