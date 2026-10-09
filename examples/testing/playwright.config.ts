// Copy into a project already using @playwright/test; adapt testDir and local startup.
import { defineConfig } from '@playwright/test';

const baseURL = process.env.KIT_BASE_URL;
const outputFile = process.env.KIT_JUNIT_PATH;
const kind = process.env.KIT_ENVIRONMENT_KIND;
if (!baseURL || !outputFile || !['local', 'dev'].includes(kind ?? '')) {
  throw new Error('Run via the configured dev-ai-kit check with an explicit environment');
}
if (kind === 'local' && !process.env.KIT_LOCAL_START_COMMAND) {
  throw new Error('Set the project-specific KIT_LOCAL_START_COMMAND after verifying its port');
}

export default defineConfig({
  testDir: './tests/api',
  workers: 1,
  retries: 0,
  timeout: 30_000,
  reporter: [['list'], ['junit', { outputFile }]],
  use: { baseURL },
  webServer: kind === 'local' ? {
    command: process.env.KIT_LOCAL_START_COMMAND!,
    url: new URL('/health', baseURL).toString(),
    reuseExistingServer: false,
    timeout: 60_000,
  } : undefined,
});
