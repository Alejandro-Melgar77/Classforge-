import { test, expect } from '@playwright/test';
import { setupMockBackend, seedUserSession } from './helpers/e2e-setup';
import { MOCK_DIAGRAM } from './helpers/mock-data';

test.describe('Escenario 5: Sesión expirada (Modal accesible y retorno a la URL)', () => {
  test('debe mostrar modal accesible ante expiración 401 y redirigir a login con returnUrl', async ({ page }) => {
    // 1. Seed session and setup base mock backend
    await seedUserSession(page);
    await setupMockBackend(page);

    // 2. Open diagram canvas
    const targetUrl = `/diagrams/${MOCK_DIAGRAM.id}`;
    await page.goto(targetUrl);
    await page.waitForSelector('.diagram-canvas-shell', { timeout: 15000 });

    // 3. Configure mock routes so that refresh token returns 401 (expired) and next save call returns 401
    await page.route('**/api/v1/auth/refresh', (route) => {
      route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({
          success: false,
          message: 'Refresh token inválido o expirado',
          code: 'UNAUTHORIZED'
        })
      });
    });

    await page.route('**/api/v1/diagrams/**/graph', (route) => {
      route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({
          success: false,
          message: 'Token de acceso expirado',
          code: 'UNAUTHORIZED'
        })
      });
    });

    // Mark graph as dirty by clicking on a classifier in the toolbox
    const classToolboxItem = page.locator('app-toolbox-palette').getByText('Clase').first();
    await classToolboxItem.click();

    // Force save with Ctrl+S which triggers HTTP save request
    await page.keyboard.press('Control+s');

    // 4. Verify Accessible Modal appears
    const modal = page.locator('app-session-expired-modal [role="alertdialog"]');
    await expect(modal).toBeVisible({ timeout: 10000 });
    await expect(page.locator('#session-expired-title')).toHaveText('Tu sesión ha expirado');
    await expect(page.locator('#session-expired-desc')).toContainText('Han transcurrido más de 30 minutos');

    // 5. Click "Iniciar sesión nuevamente"
    const reloginBtn = modal.locator('button:has-text("Iniciar sesión nuevamente")');
    await expect(reloginBtn).toBeVisible();
    await reloginBtn.click();

    // 6. Verify redirection to /auth/login with returnUrl query param
    await page.waitForURL((url) => url.pathname.includes('/auth/login'), { timeout: 10000 });
    expect(page.url()).toContain('/auth/login');
    expect(page.url()).toContain('returnUrl');
    expect(page.url()).toContain(encodeURIComponent(targetUrl));
  });
});
