import { HttpRequest, HttpHandlerFn, HttpResponse, HttpHeaders } from '@angular/common/http';
import { of } from 'rxjs';
import { geminiKeyInterceptor, GEMINI_BYOK_STORAGE_KEY } from './gemini-key.interceptor';

describe('geminiKeyInterceptor', () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  afterEach(() => {
    sessionStorage.clear();
  });

  it('should attach X-Gemini-Key header when key is in sessionStorage', (done) => {
    sessionStorage.setItem(GEMINI_BYOK_STORAGE_KEY, 'AIzaSyTest123456');

    const req = new HttpRequest('GET', '/api/v1/ai-chat/projects/p1/messages');
    const next: HttpHandlerFn = (clonedReq) => {
      expect(clonedReq.headers.get('X-Gemini-Key')).toBe('AIzaSyTest123456');
      return of(new HttpResponse({ status: 200 }));
    };

    geminiKeyInterceptor(req, next).subscribe({
      next: () => done(),
      error: done.fail
    });
  });

  it('should not attach X-Gemini-Key header when sessionStorage is empty', (done) => {
    const req = new HttpRequest('GET', '/api/v1/ai-chat/projects/p1/messages');
    const next: HttpHandlerFn = (clonedReq) => {
      expect(clonedReq.headers.has('X-Gemini-Key')).toBeFalse();
      return of(new HttpResponse({ status: 200 }));
    };

    geminiKeyInterceptor(req, next).subscribe({
      next: () => done(),
      error: done.fail
    });
  });

  it('should not override X-Gemini-Key header if already present in request', (done) => {
    sessionStorage.setItem(GEMINI_BYOK_STORAGE_KEY, 'sessionKey');

    const req = new HttpRequest('GET', '/api/v1/ai-chat/projects/p1/messages', {
      headers: new HttpHeaders({ 'X-Gemini-Key': 'explicitKey' })
    });
    const next: HttpHandlerFn = (clonedReq) => {
      expect(clonedReq.headers.get('X-Gemini-Key')).toBe('explicitKey');
      return of(new HttpResponse({ status: 200 }));
    };

    geminiKeyInterceptor(req, next).subscribe({
      next: () => done(),
      error: done.fail
    });
  });
});
