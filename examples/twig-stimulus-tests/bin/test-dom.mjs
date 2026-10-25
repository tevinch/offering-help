import { randomUUID } from 'node:crypto';
import { spawnSync } from 'node:child_process';

const env = { ...process.env, FIXTURE_RUN_ID: randomUUID() };
for (const [command, args] of [
  [process.env.PHP_BINARY || 'php', ['bin/render-fixture.php', env.FIXTURE_RUN_ID]],
  [process.execPath, ['--test', 'tests/dom/title-count.test.mjs']],
]) {
  const result = spawnSync(command, args, { env, stdio: 'inherit' });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status ?? 1);
}
