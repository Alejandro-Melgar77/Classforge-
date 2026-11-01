import { ApplicationConfig, importProvidersFrom } from '@angular/core';
import { provideRouter, withComponentInputBinding } from '@angular/router';
import { routes } from './app.routes';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { jwtInterceptor } from './core/interceptors/jwt.interceptor';
import { geminiKeyInterceptor } from './core/interceptors/gemini-key.interceptor';
import { errorInterceptor } from './core/interceptors/error.interceptor';
import { 
  LucideAngularModule, 
  Plus, 
  X, 
  Settings2, 
  Settings, 
  MousePointer2, 
  Hand, 
  Square, 
  Diamond, 
  Braces, 
  AlignStartVertical, 
  StickyNote, 
  ArrowRight, 
  CornerDownRight, 
  Share2, 
  Expand, 
  Save, 
  Download, 
  Upload,
  Undo, 
  Redo, 
  Trash2, 
  Copy,
  ClipboardPaste,
  BoxSelect, 
  Maximize,
  ZoomIn,
  ZoomOut,
  LayoutGrid,
  Layout,
  Package,
  ChevronDown,
  ChevronRight,
  Hexagon,
  ArrowUpRight
} from 'lucide-angular';

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes, withComponentInputBinding()),
    provideHttpClient(withInterceptors([jwtInterceptor, geminiKeyInterceptor, errorInterceptor])),
    importProvidersFrom(
      LucideAngularModule.pick({
        Plus,
        X,
        Settings2,
        Settings,
        MousePointer2,
        Hand,
        Square,
        Diamond,
        Braces,
        AlignStartVertical,
        StickyNote,
        ArrowRight,
        CornerDownRight,
        Share2,
        Expand,
        Save,
        Download,
        Upload,
        Undo,
        Redo,
        Trash2,
        Copy,
        ClipboardPaste,
        BoxSelect,
        Maximize,
        ZoomIn,
        ZoomOut,
        LayoutGrid,
        Layout,
        Package,
        ChevronDown,
        ChevronRight,
        Hexagon,
        ArrowUpRight
      })
    )
  ]
};
