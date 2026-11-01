import { HttpInterceptorFn, HttpRequest, HttpHandlerFn } from '@angular/common/http';

export const GEMINI_BYOK_STORAGE_KEY = 'classforge_gemini_api_key';

/**
 * Attaches the BYOK Gemini API key from sessionStorage via X-Gemini-Key header
 * only when explicitly provided by the user.
 */
export const geminiKeyInterceptor: HttpInterceptorFn = (
  req: HttpRequest<unknown>,
  next: HttpHandlerFn
) => {
  if (typeof sessionStorage !== 'undefined') {
    const key = sessionStorage.getItem(GEMINI_BYOK_STORAGE_KEY);
    if (key && key.trim() && !req.headers.has('X-Gemini-Key')) {
      const clonedReq = req.clone({
        setHeaders: {
          'X-Gemini-Key': key.trim()
        }
      });
      return next(clonedReq);
    }
  }
  return next(req);
};
