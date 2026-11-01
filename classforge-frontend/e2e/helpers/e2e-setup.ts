import { Page, Route } from '@playwright/test';
import {
  MOCK_USER_ALICE,
  MOCK_USER_BOB,
  MOCK_PROJECT,
  MOCK_DIAGRAM,
  MOCK_HISTORY_ENTRIES,
  MOCK_AI_TEAM_STATE,
  MOCK_AI_PROPOSAL
} from './mock-data';

export interface SetupOptions {
  user?: any;
  project?: any;
  diagram?: any;
  history?: any[];
  aiState?: any;
  expireSessionOnFirstCall?: boolean;
}

export async function setupMockBackend(page: Page, options: SetupOptions = {}) {
  const currentUser = options.user || MOCK_USER_ALICE;
  const project = options.project || MOCK_PROJECT;
  const currentDiagram = JSON.parse(JSON.stringify(options.diagram || MOCK_DIAGRAM));
  const historyEntries = [...(options.history || MOCK_HISTORY_ENTRIES)];
  const aiState = JSON.parse(JSON.stringify(options.aiState || MOCK_AI_TEAM_STATE));

  let shouldExpire = options.expireSessionOnFirstCall || false;

  await page.route('**/api/v1/**', async (route: Route) => {
    const rawUrl = route.request().url();
    const [url] = rawUrl.split('?');
    const method = route.request().method();

    // Check if session should expire with 401
    if (shouldExpire && !url.includes('/auth/login') && !url.includes('/auth/refresh')) {
      shouldExpire = false;
      return route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({
          success: false,
          message: 'Token de acceso expirado',
          code: 'UNAUTHORIZED'
        })
      });
    }

    // ── Auth Endpoints ──
    if (url.includes('/auth/login') && method === 'POST') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          message: 'Sesión iniciada correctamente',
          data: {
            access_token: 'fake-jwt-token-alice',
            refresh_token: 'fake-refresh-token-alice',
            token_type: 'bearer',
            user: currentUser
          }
        })
      });
    }

    if (url.includes('/auth/refresh') && method === 'POST') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          message: 'Token renovado',
          data: {
            access_token: 'fake-jwt-token-refreshed',
            refresh_token: 'fake-refresh-token-refreshed',
            token_type: 'bearer',
            user: currentUser
          }
        })
      });
    }

    if (url.includes('/auth/me') && method === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: currentUser
        })
      });
    }

    if (url.includes('/auth/sessions')) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: [] })
      });
    }

    // ── Notifications ──
    if (url.includes('/notifications')) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: [] })
      });
    }

    // ── Dashboard ──
    if (url.includes('/dashboard')) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            total_projects: 1,
            total_diagrams: 1,
            active_collaborators: 2,
            recent_diagrams: [currentDiagram]
          }
        })
      });
    }

    // ── Projects Endpoints ──
    if (url.endsWith('/projects/mine') || url.endsWith('/projects')) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [project]
        })
      });
    }

    if (url.includes(`/projects/${project.id}/diagrams`) && method === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [currentDiagram]
        })
      });
    }

    if (url.includes(`/projects/${project.id}/members`) && method === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [MOCK_USER_ALICE, MOCK_USER_BOB]
        })
      });
    }

    if (url.includes(`/projects/${project.id}/tasks`) && method === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: []
        })
      });
    }

    if (url.includes(`/projects/${project.id}`) && method === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: project
        })
      });
    }

    // ── Diagrams Endpoints ──
    if (url.includes(`/diagrams/${currentDiagram.id}/history/`) && url.includes('/restore') && method === 'POST') {
      const match = url.match(/\/history\/(\d+)\/restore/);
      const versionNum = match ? parseInt(match[1], 10) : 1;
      currentDiagram.version = versionNum + 1;
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          message: `Diagrama restaurado a la versión ${versionNum}`,
          data: currentDiagram
        })
      });
    }

    if (url.includes(`/diagrams/${currentDiagram.id}/history`) && method === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: historyEntries
        })
      });
    }

    if (url.includes(`/diagrams/${currentDiagram.id}/ws-token`)) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            token: 'mock-ws-token-alice-12345',
            expires_at: new Date(Date.now() + 3600000).toISOString()
          }
        })
      });
    }

    if (url.includes(`/diagrams/${currentDiagram.id}/graph`) && method === 'PUT') {
      const postData = route.request().postDataJSON();
      if (postData?.graph_data) {
        currentDiagram.graph_data = postData.graph_data;
      }
      currentDiagram.version = (currentDiagram.version || 1) + 1;
      currentDiagram.updated_at = new Date().toISOString();
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          message: 'Grafo guardado exitosamente',
          data: currentDiagram
        })
      });
    }

    if (url.includes(`/diagrams/${currentDiagram.id}`) && method === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: currentDiagram
        })
      });
    }

    if (url.endsWith('/diagrams') && method === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [currentDiagram]
        })
      });
    }

    if (url.endsWith('/diagrams') && method === 'POST') {
      const newDiagram = {
        ...currentDiagram,
        id: `diag-created-${Date.now()}`,
        name: 'Nuevo Diagrama E2E',
        version: 1
      };
      return route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: newDiagram
        })
      });
    }

    // ── AI Team & Chat Endpoints ──
    if (url.includes('/ai-team/state') || (url.includes('/ai-chat') && url.includes('/state'))) {
      if (method === 'PATCH' || method === 'POST') {
        const body = route.request().postDataJSON();
        if (body?.participative) {
          aiState.participative.enabled = body.participative.enabled;
        }
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true, data: aiState })
        });
      }
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: aiState })
      });
    }

    if (url.includes('/ai/command') || url.includes('/ai/generate') || url.includes('/ai-chat/send')) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            command: MOCK_AI_PROPOSAL,
            response: 'Propuesta generada por el Arquitecto de Software.',
            has_diagram_changes: true
          }
        })
      });
    }

    // Fallback: continue request
    await route.continue();
  });
}

/**
 * Pre-seeds session storage and local storage to skip form login in inner tests.
 */
export async function seedUserSession(page: Page, user = MOCK_USER_ALICE) {
  await page.addInitScript((userData) => {
    localStorage.setItem('cf_user', JSON.stringify(userData));
    localStorage.setItem('cf_refresh_token', 'seed-fake-refresh-token');
    sessionStorage.setItem('cf_user', JSON.stringify(userData));
    sessionStorage.setItem('cf_refresh_token', 'seed-fake-refresh-token');
  }, user);
}

/**
 * Performs explicit UI login through the login page form.
 */
export async function loginViaUI(page: Page, email = 'alice@classforge.io', password = 'Password123!') {
  await page.goto('/auth/login');
  await page.waitForSelector('form');

  await page.fill('input[formControlName="email"]', email);
  await page.fill('input[formControlName="password"]', password);

  const submitBtn = page.locator('button[type="submit"]');
  await submitBtn.click();

  // Wait for redirect to dashboard or project page
  await page.waitForURL((url) => !url.pathname.includes('/auth/login'), { timeout: 10000 });
}
