import { test, expect } from '@playwright/test';
import { setupMockBackend, seedUserSession } from './helpers/e2e-setup';
import { MOCK_USER_ALICE, MOCK_USER_BOB, MOCK_DIAGRAM } from './helpers/mock-data';

test.describe('Escenario 3: Dos contextos de navegador (Locks, OP_REJECTED, Presencia e Historial)', () => {
  test('debe sincronizar presencia, mostrar lock de nodo con dueño, revertir con OP_REJECTED y permitir ver historial', async ({ browser }) => {
    // 1. Create two isolated browser contexts
    const contextAlice = await browser.newContext();
    const contextBob = await browser.newContext();

    const pageAlice = await contextAlice.newPage();
    const pageBob = await contextBob.newPage();

    // Setup backend mocks for both contexts
    await seedUserSession(pageAlice, MOCK_USER_ALICE);
    await setupMockBackend(pageAlice, { user: MOCK_USER_ALICE });

    await seedUserSession(pageBob, MOCK_USER_BOB);
    await setupMockBackend(pageBob, { user: MOCK_USER_BOB });

    // 2. Intercept WebSockets to simulate collaborative broker
    let wsAlice: any = null;
    let wsBob: any = null;

    const roomState = {
      type: 'ROOM_STATE',
      users: [
        { user_id: MOCK_USER_ALICE.id, user_name: MOCK_USER_ALICE.name, user_color: '#3B82F6', status: 'online' },
        { user_id: MOCK_USER_BOB.id, user_name: MOCK_USER_BOB.name, user_color: '#8B5CF6', status: 'online' }
      ]
    };

    await pageAlice.routeWebSocket(/.*\/ws\/.*/, (ws) => {
      wsAlice = ws;
      ws.onMessage((msg) => {
        const str = typeof msg === 'string' ? msg : msg.toString();
        try {
          const data = JSON.parse(str);
          if (data.type === 'JOIN') {
            ws.send(JSON.stringify(roomState));
          }
        } catch {}
      });
      setTimeout(() => {
        try { ws.send(JSON.stringify(roomState)); } catch {}
      }, 200);
    });

    await pageBob.routeWebSocket(/.*\/ws\/.*/, (ws) => {
      wsBob = ws;
      ws.onMessage((msg) => {
        const str = typeof msg === 'string' ? msg : msg.toString();
        try {
          const data = JSON.parse(str);
          if (data.type === 'JOIN') {
            ws.send(JSON.stringify(roomState));
          }
        } catch {}
      });
      setTimeout(() => {
        try { ws.send(JSON.stringify(roomState)); } catch {}
      }, 200);
    });

    // 3. Open diagram canvas in both browsers
    await Promise.all([
      pageAlice.goto(`/diagrams/${MOCK_DIAGRAM.id}`),
      pageBob.goto(`/diagrams/${MOCK_DIAGRAM.id}`)
    ]);

    await Promise.all([
      pageAlice.waitForSelector('.diagram-canvas-shell', { timeout: 15000 }),
      pageBob.waitForSelector('.diagram-canvas-shell', { timeout: 15000 })
    ]);

    // 4. Presence Verification: Alice sees Bob's avatar in presence bar
    const alicePresenceBar = pageAlice.locator('app-presence-bar');
    await expect(alicePresenceBar).toBeVisible();
    await expect(alicePresenceBar.locator('.avatar, .avatar-container').first()).toBeVisible({ timeout: 10000 });

    // 5. Node Lock Simulation: Bob locks node-order via LOCK_GRANTED
    if (wsAlice) {
      wsAlice.send(JSON.stringify({
        type: 'LOCK_GRANTED',
        element_id: 'node-order',
        user_id: MOCK_USER_BOB.id
      }));
    }

    // Alice should see the locked badge with Bob's name
    const lockBadge = pageAlice.locator('.lock-badge');
    await expect(lockBadge).toBeVisible({ timeout: 8000 });
    await expect(lockBadge).toContainText(MOCK_USER_BOB.name);

    // 6. OP_REJECTED Simulation: Server rejects operation and Alice receives rollback notification
    if (wsAlice) {
      wsAlice.send(JSON.stringify({
        type: 'OP_REJECTED',
        element_id: 'node-order',
        reason: 'locked'
      }));
    }

    // Verify warning toast appears in Alice's window
    const toast = pageAlice.getByText('Operación rechazada').first();
    await expect(toast).toBeVisible({ timeout: 8000 });

    // 7. Version History Modal: Bob opens history modal
    const historyBtn = pageBob.locator('button[aria-label="Historial de versiones"], button[title*="historial"]').first();
    await expect(historyBtn).toBeVisible();
    await historyBtn.click();

    // Verify history modal opens and displays versions v1 and v2
    const historyModalTitle = pageBob.locator('#history-modal-title');
    await expect(historyModalTitle).toBeVisible({ timeout: 8000 });
    await expect(pageBob.locator('text=v1').first()).toBeVisible();
    await expect(pageBob.locator('text=v2').first()).toBeVisible();

    // Cleanup contexts
    await contextAlice.close();
    await contextBob.close();
  });
});
