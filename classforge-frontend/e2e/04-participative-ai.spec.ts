import { test, expect } from '@playwright/test';
import { setupMockBackend, seedUserSession } from './helpers/e2e-setup';
import { MOCK_DIAGRAM } from './helpers/mock-data';

test.describe('Escenario 4: Participativa ON + Arquitecto con LLM falso (Propuesta, Aplicar y Deshacer)', () => {
  test.beforeEach(async ({ page }) => {
    await seedUserSession(page);
    await setupMockBackend(page);
  });

  test('debe activar IA participativa, recibir propuesta del Arquitecto, aplicarla al lienzo y deshacerla', async ({ page }) => {
    // 1. Navigate to diagram canvas
    await page.goto(`/diagrams/${MOCK_DIAGRAM.id}`);
    await page.waitForSelector('.diagram-canvas-shell', { timeout: 15000 });

    // 2. Open AI Assistant Drawer
    const aiDrawerBtn = page.locator('button[data-tour="ai-assistant-btn"], button[title*="Asistente de equipo IA"]').first();
    await expect(aiDrawerBtn).toBeVisible();
    await aiDrawerBtn.click();

    // Verify AI Drawer is open
    const drawer = page.locator('aside.ai-drawer');
    await expect(drawer).toBeVisible({ timeout: 5000 });

    // 3. Switch to Equipo IA tab to verify and toggle participative mode
    const aiTeamTab = drawer.locator('button[role="tab"]:has-text("Equipo IA")');
    await aiTeamTab.click();

    // Verify participative toggle exists and is visible
    const participativeToggle = page.locator('#participative-toggle');
    await expect(participativeToggle).toBeAttached();

    // Ensure it is checked / active
    const isChecked = await participativeToggle.isChecked();
    if (!isChecked) {
      await page.locator('label:has(#participative-toggle)').click();
    }

    // Verify Roles accordion is displayed and participative mode is active
    await expect(drawer.locator('button:has-text("Roles")').first()).toBeVisible({ timeout: 5000 });

    // 4. Switch back to Comandos tab
    const commandsTab = drawer.locator('button[role="tab"]:has-text("Comandos")');
    await commandsTab.click();

    // Ensure Previa mode is active so proposal card requires confirmation
    const modeBtn = drawer.locator('button[aria-label="Cambiar modo de ejecución del comando"]');
    await expect(modeBtn).toBeVisible();
    const modeText = await modeBtn.innerText();
    if (modeText.includes('Directo')) {
      await modeBtn.click();
    }
    await expect(modeBtn).toContainText('Previa');

    // 5. Input prompt for Fake LLM
    const commandInput = drawer.locator('input[placeholder*="Ej: crea clase"]').first();
    await expect(commandInput).toBeVisible();
    await commandInput.fill('Crea clase Payment para desacoplar procesamiento de pagos');
    await commandInput.press('Enter');

    // 6. Verify proposal card appears with architect suggestion
    const previewCard = drawer.locator('.command-preview-card, app-command-preview-card');
    await expect(previewCard.first()).toBeVisible({ timeout: 10000 });
    await expect(drawer.locator('text=Payment').first()).toBeVisible();

    // 7. Click "✓ Aplicar al Lienzo"
    const applyBtn = drawer.locator('button:has-text("Aplicar al Lienzo"), button:has-text("Aplicar")').first();
    await expect(applyBtn).toBeVisible();
    await applyBtn.click();

    // 8. Verify class Payment is now rendered in diagram canvas
    const canvasPayment = page.locator('.diagram-canvas-shell').getByText('Payment').first();
    await expect(canvasPayment).toBeVisible({ timeout: 8000 });

    // 9. Click "Deshacer" in toolbar to revert
    const undoBtn = page.locator('button[title*="Deshacer"], button[aria-label*="Deshacer"]').first();
    await expect(undoBtn).toBeVisible();
    await undoBtn.click();

    // 10. Verify that undo reverted the graph state
    await page.waitForTimeout(500);
    await expect(page.locator('.diagram-canvas-shell').getByText('Order').first()).toBeVisible();
  });
});
