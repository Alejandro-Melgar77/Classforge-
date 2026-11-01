import { test, expect } from '@playwright/test';
import { setupMockBackend, loginViaUI } from './helpers/e2e-setup';
import { MOCK_PROJECT } from './helpers/mock-data';

test.describe('Escenario 1: Recorrido de navegación completo (UX Audit)', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockBackend(page);
  });

  test('debe autenticar, navegar por dashboard, proyectos y todas las pestañas del centro de proyecto', async ({ page }) => {
    // 1. Login
    await loginViaUI(page, 'alice@classforge.io', 'Password123!');
    expect(page.url()).toContain('/dashboard');

    // 2. Dashboard metrics and layout check
    await expect(page.locator('h1').first()).toBeVisible();

    // 3. Navigate to Projects (via sidebar or URL)
    const projectsNav = page.locator('a[routerLink="/projects"], a[href*="/projects"]').first();
    if (await projectsNav.isVisible()) {
      await projectsNav.click();
    } else {
      await page.goto('/projects');
    }
    await page.waitForURL((url) => url.pathname.includes('/projects'));

    // 4. Click project card to enter Project Center
    const projectCard = page.locator(`text=${MOCK_PROJECT.name}`).first();
    await expect(projectCard).toBeVisible({ timeout: 10000 });
    await projectCard.click();

    // Wait for project center to load and redirect to /resumen
    await page.waitForURL((url) => url.pathname.includes(`/projects/${MOCK_PROJECT.id}`));

    // 5. Verify Resumen tab
    await expect(page.locator('a[routerLink="resumen"]')).toBeVisible();
    await expect(page.getByText(MOCK_PROJECT.name, { exact: false }).first()).toBeVisible();

    // 6. Navigate to Diagramas tab
    const diagramsTab = page.locator('a[routerLink="diagramas"]');
    await diagramsTab.click();
    await page.waitForURL((url) => url.pathname.includes('/diagramas'));
    await expect(page.locator('text=Diagrama de Ordenes').first()).toBeVisible({ timeout: 5000 });

    // 7. Navigate to Equipo IA tab
    const aiTeamTab = page.locator('a[routerLink="equipo-ia"]');
    await aiTeamTab.click();
    await page.waitForURL((url) => url.pathname.includes('/equipo-ia'));
    await expect(page.locator('app-ai-team-panel, [role="region"], app-ai-team-header').first()).toBeVisible();

    // 8. Navigate to Tareas tab
    const tasksTab = page.locator('a[routerLink="tareas"]');
    await tasksTab.click();
    await page.waitForURL((url) => url.pathname.includes('/tareas'));

    // 9. Navigate to Miembros tab
    const membersTab = page.locator('a[routerLink="miembros"]');
    await membersTab.click();
    await page.waitForURL((url) => url.pathname.includes('/miembros'));
    await expect(page.locator('text=Alice Dev').first()).toBeVisible();

    // 10. Click Back to Projects button
    const backBtn = page.locator('button:has-text("Proyectos")').first();
    await backBtn.click();
    await page.waitForURL((url) => url.pathname.includes('/projects'));
  });
});
