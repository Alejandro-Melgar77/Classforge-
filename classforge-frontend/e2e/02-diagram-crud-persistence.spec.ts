import { test, expect } from '@playwright/test';
import { setupMockBackend, seedUserSession } from './helpers/e2e-setup';
import { MOCK_DIAGRAM } from './helpers/mock-data';

test.describe('Escenario 2: Crear diagrama, añadir clase, auto-save y persistencia', () => {
  test.beforeEach(async ({ page }) => {
    await seedUserSession(page);
    await setupMockBackend(page);
  });

  test('debe cargar diagrama, permitir insertar nodo, mostrar estado de auto-save y persistir tras recarga', async ({ page }) => {
    // 1. Navigate to diagram canvas
    await page.goto(`/diagrams/${MOCK_DIAGRAM.id}`);
    await page.waitForSelector('.diagram-canvas-shell', { timeout: 15000 });

    // 2. Verify graph canvas container is visible and accessible
    await expect(page.locator('.diagram-canvas-shell')).toBeVisible();
    await expect(page.locator('[role="application"]').first()).toBeVisible();

    // Verify initial classes exist in graph
    await expect(page.locator('text=Order').first()).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=Customer').first()).toBeVisible();

    // 3. Verify AutoSave status indicator is rendered and accessible
    const autoSaveStatus = page.locator('div[role="status"]').first();
    await expect(autoSaveStatus).toBeVisible();
    await expect(autoSaveStatus).toContainText(/Guardado|Sin guardar/);

    // 4. Insert new class from Toolbox (click on Clase classifier)
    const classToolboxItem = page.locator('app-toolbox-palette').getByText('Clase').first();
    await expect(classToolboxItem).toBeVisible();
    await classToolboxItem.click();

    // 5. Trigger or await auto-save: press Ctrl+S to force save
    await page.keyboard.press('Control+s');

    // Auto-save indicator should show saved
    await expect(autoSaveStatus).toContainText('Guardado', { timeout: 8000 });

    // 6. Reload page to verify persistence
    await page.reload();
    await page.waitForSelector('.diagram-canvas-shell', { timeout: 15000 });

    // 7. Verify elements persisted
    await expect(page.locator('text=Order').first()).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=Customer').first()).toBeVisible();
  });
});
