# Auditoría UX y Navegabilidad — ClassForge (P7a)

**Fecha:** 1 de noviembre de 2026  
**Auditor:** Agente Antigravity (P7a Shell, Rutas y Centro de Proyecto)  
**Alcance:** Frontend (classforge-frontend), Enrutamiento (pp.routes.ts y feature routes), Shell, Responsive (360px, 768px, 1280px), Brechas con Backend (classforge-backend), Calidad de Código y Accesibilidad.

---

## 1. Inventario Completo de Rutas y Accesibilidad desde UI

| Ruta | Componente Host | Desde dónde se llega en UI | ¿Alcanzable por clics? | Estado P7a |
|---|---|---|---|---|
| /auth/login | LoginComponent | Redirección inicial si no auth, enlace \'Iniciar sesión\' en registro, botón \'Cerrar sesión\' | Sí | **RESUELTO** |
| /auth/register | RegisterComponent | Enlace \'¿No tienes cuenta? Regístrate\' en /auth/login | Sí | **RESUELTO** |
| /auth | Redirige a /auth/login | Navegación a /auth | Sí | **RESUELTO** |
| / | Redirige a /dashboard | Raíz protegida por uthGuard | Sí | **RESUELTO** |
| /dashboard | DashboardComponent | Ítem \'Inicio\' en barra lateral / *bottom-nav* | Sí | **RESUELTO** |
| /projects | Redirige a /projects/mine | Ítem \'Proyectos\' en barra lateral / *bottom-nav* | Sí | **RESUELTO** |
| /projects/mine | RepertoireComponent | Sub-ítem \'Mis Proyectos\' o ítem \'Proyectos\' | Sí | **RESUELTO** |
| /projects/teams | RepertoireComponent | Ítem \'Mis Equipos\' en barra lateral / *bottom-nav* | Sí | **RESUELTO** |
| /projects/:projectId | ProjectCenterComponent | Clic en tarjeta de proyecto en Repertorio o Dashboard | Sí | **RESUELTO** |
| /projects/:projectId/resumen | ProjectOverviewComponent | Pestaña \'Resumen\' del Centro de Proyecto | Sí | **RESUELTO** |
| /projects/:projectId/diagramas | ProjectDiagramsComponent | Pestaña \'Diagramas\' del Centro de Proyecto | Sí | **RESUELTO** |
| /projects/:projectId/equipo-ia | ProjectAiTeamComponent | Pestaña \'Equipo IA\' del Centro de Proyecto o botón 🤖 en tarjeta | Sí | **RESUELTO** |
| /projects/:projectId/tareas | ProjectTasksComponent | Pestaña \'Tareas\' del Centro de Proyecto | Sí | **RESUELTO** |
| /projects/:projectId/miembros | ProjectMembersComponent | Pestaña \'Miembros\' del Centro de Proyecto | Sí | **RESUELTO** |
| /diagrams | DiagramListComponent | Ítem \'Diagramas\' en barra lateral / *bottom-nav* | Sí | **RESUELTO** |
| /diagrams/:id | DiagramCanvasComponent | Clic en diagrama desde lista o Centro de Proyecto | Sí | **RESUELTO** |
| /admin | Redirige a /admin/users | Ítem \'Administración\' en barra lateral (solo admin) | Sí | **RESUELTO** |
| /admin/users | UserListComponent | Sub-ítem \'Usuarios\' en barra lateral y pestaña Admin | Sí | **RESUELTO** |
| /admin/teams | TeamListComponent | Sub-ítem \'Equipos\' en barra lateral y pestaña Admin | Sí | **RESUELTO** |
| /admin/config | GlobalConfigComponent | Sub-ítem \'Configuración\' en barra lateral y pestaña Admin | Sí | **RESUELTO** |
| /ai-chat/:projectId | Redirige a /projects/:projectId/equipo-ia | Redirección transparente de enlaces antiguos | Sí | **RESUELTO** |
| /ai-chat | Redirige a /projects | Redirección transparente de rutas obsoletas | Sí | **RESUELTO** |

---

## 2. Rutas Huérfanas y Soluciones Implementadas

1. **Centro de Proyecto (/projects/:projectId):**
   - **Severidad Inicial: P1 (Bloqueante)**
   - **Diagnóstico previo:** Los proyectos se listaban en el repertorio pero los clics no abrían ningún detalle.
   - **Solución P7a: RESUELTO** — Creado ProjectCenterComponent con 5 pestañas hijas (/resumen, /diagramas, /equipo-ia, /tareas, /miembros), botón \'← Volver a Proyectos\', breadcrumbs reactivos con nombre dinámico del proyecto y control de permisos/errores (PageStateComponent).

2. **Equipo IA a Pantalla Completa (/projects/:projectId/equipo-ia):**
   - **Severidad Inicial: P1 (Bloqueante)**
   - **Diagnóstico previo:** El botón de chat en la tarjeta de proyecto redirigía erróneamente de vuelta al repertorio.
   - **Solución P7a: RESUELTO** — Se implementó ProjectAiTeamComponent embebiendo AiTeamPanelComponent a pantalla completa. Además, la ruta /ai-chat/:projectId redirige automáticamente a /projects/:projectId/equipo-ia.

3. **Gestión de Perfil de Usuario:**
   - **Severidad Inicial: P1 (Crítico)**
   - **Diagnóstico previo:** El backend soportaba PUT /api/v1/auth/profile, pero no existía interfaz interactiva para editar datos ni ver rol.
   - **Solución P7a: RESUELTO** — Implementado UserMenuModalComponent con pestaña Perfil (edición de nombre y avatar), accesible desde el avatar en la cabecera.

4. **Centro de Notificaciones:**
   - **Severidad Inicial: P1 (Crítico)**
   - **Diagnóstico previo:** Endpoints existentes en backend sin presencia en la barra superior.
   - **Solución P7a: RESUELTO** — Implementado NotificationsPanelComponent desplegable desde la campana con contador reactivo, filtro de no leídas, marcar todas como leídas y eliminación individual.

---

## 3. Callejones sin Salida (Dead Ends) Resueltos

1. **Diagram Canvas (/diagrams/:id):**
   - **Problema previo:** El botón \'Volver\' navegaba rígidamente a /diagrams, perdiendo el proyecto origen.
   - **Solución P7a: RESUELTO** — Se añadió goBack() contextual: si el diagrama pertenece a un proyecto (project_id), regresa a /projects/:projectId/diagramas; de lo contrario, regresa a /diagrams. Se integraron breadcrumbs en la cabecera global.

2. **Vistas de Administración (/admin/*):**
   - **Problema previo:** Sin breadcrumbs ni navegación de regreso explícita.
   - **Solución P7a: RESUELTO** — Breadcrumbs presentes en todo momento (Inicio > Administración > Usuarios/Equipos/Configuración) con navegación hacia cualquier nivel padre con un clic.

3. **Manejo de Errores 403 / 404:**
   - **Problema previo:** Pantallas en blanco o errores no gestionados.
   - **Solución P7a: RESUELTO** — Integración de PageStateComponent en ProjectCenterComponent y vistas principales: ante 404 o 403 se muestra mensaje descriptivo en español con botón \'Volver a Proyectos\' y reintento.

---

## 4. Acciones del Backend sin Interfaz de Usuario (UI) — Estado

| Endpoint Backend | Funcionalidad | ¿Presente en UI? | Prioridad | Estado de Implementación P7a |
|---|---|---|---|---|
| POST /api/v1/diagrams/{id}/import/xmi | Importación XMI a diagrama | **SÍ** | **P1** | **RESUELTO:** Botón \'Importar XMI\' en Canvas y en ProjectDiagramsComponent. |
| GET /api/v1/diagrams/{id}/history | Historial de versiones del diagrama | **SÍ** | **P1** | **RESUELTO:** Badge de versión clickeable en Canvas abre modal con historial cronológico. |
| POST /api/v1/diagrams/{id}/history/{v}/restore | Restaurar versión previa | **SÍ** | **P1** | **RESUELTO:** Botón \'Restaurar\' con confirmación destructiva en modal de historial. |
| GET /api/v1/diagrams/{id}/export/xmi | Exportación XMI | **SÍ** | P3 | **RESUELTO:** Botón \'XMI\' en toolbar del Canvas y en Centro de Proyecto. |
| GET /api/v1/diagrams/{id}/export/json | Exportación JSON | **SÍ** | P3 | **RESUELTO:** Botón \'{ } JSON\' en toolbar del Canvas. |
| GET /api/v1/auth/sessions | Listar sesiones activas | **SÍ** | **P1** | **RESUELTO:** Pestaña \'Sesiones Activas\' en UserMenuModalComponent con IP y fecha. |
| POST /api/v1/auth/logout-all | Cerrar todas las sesiones activas | **SÍ** | **P1** | **RESUELTO:** Botón en UserMenuModalComponent con diálogo de confirmación. |
| POST /api/v1/auth/change-password | Cambio de contraseña | **SÍ** | **P1** | **RESUELTO:** Pestaña \'Seguridad\' en UserMenuModalComponent. |
| PUT /api/v1/auth/profile | Actualización de perfil | **SÍ** | **P1** | **RESUELTO:** Pestaña \'Perfil\' en UserMenuModalComponent con ToastService. |
| GET /api/v1/notifications | Listar notificaciones y badge | **SÍ** | **P1** | **RESUELTO:** Campana con contador no leídas y panel flotante en cabecera. |
| PUT /api/v1/notifications/read-all | Marcar todas como leídas | **SÍ** | **P1** | **RESUELTO:** Botón en NotificationsPanelComponent. |
| DELETE /api/v1/notifications/{id} | Eliminar notificación | **SÍ** | **P1** | **RESUELTO:** Botón de descarte individual en cada ítem de notificación. |
| GET /api/v1/users/{id}/audit-log | Historial de auditoría por usuario | **SÍ** | **P2** | **RESUELTO:** Botón 📜 en tabla de usuarios en Admin con modal de logs. |
| PUT /api/v1/projects/{id} | Actualización de proyecto | **SÍ** | **P1** | **RESUELTO:** Selector de estado y edición en ProjectOverviewComponent. |
| DELETE /api/v1/projects/{id} | Eliminación de proyecto | **SÍ** | **P1** | **RESUELTO:** Botón con confirmación destructiva en Centro de Proyecto. |

---

## 5. Análisis de Responsividad (360px, 768px, 1280px)

### 360 px (Smartphone compacto) — **RESUELTO**
- **Navegación:** La barra lateral colapsa completamente y se activa una barra de navegación inferior (*bottom-nav*) fija con accesos directos táctiles (Inicio, Proyectos, Diagramas, Equipos, Menú).
- **Tablas:** Contenedores con desplazamiento suave (overflow-x-auto) e indicadores visuales de scroll.
- **Top bar de Canvas:** Botones secundarios compactados con íconos representativos y tooltips.
- **Controles táctiles:** Elementos con altura mínima de 44px para cumplimiento de accesibilidad táctil.

### 768 px (Tablet / Pantalla intermedia) — **RESUELTO**
- **Barra lateral:** Colapso a modo compacto (íconos estilizados) o expandido según preferencia del usuario.
- **Cabecera unificada:** Breadcrumbs responsivos con truncamiento elegante de texto largo y accesos rápidos a notificaciones y perfil.

### 1280 px (Escritorio estándar) — **RESUELTO**
- **Aprovechamiento visual:** Barra superior completa con migas de pan jerárquicas, atajos de teclado (?), panel de notificaciones y menú contextual de usuario.

---

## 6. Auditoría de Código: lert(...), console.* y Calidad

### Llamadas Nativas lert(...) y confirm(...) (32 ocurrencias eliminadas)
- **Estado: RESUELTO (100 % eliminadas)**
- Se implementaron y desplegaron transversalmente:
  1. ToastService (success, error, info, warning) montado en ToastContainerComponent accesible con ria-live.
  2. ConfirmDialogService (confirm(...) con promesa) montado en ConfirmDialogComponent con foco atrapado y tecla Escape.
- Eliminadas de:
  - inactivity.service.ts: aviso de 5 minutos reemplazado por 	oastService.warning(...).
  - 	eam-list.component.ts: 8 alertas/confirms reemplazados por toasts y diálogo accesible.
  - user-list.component.ts: 7 alertas/confirms reemplazados por toasts y diálogo accesible.
  - diagram-canvas.component.ts: 7 alertas/confirms reemplazados por toasts y diálogo accesible.
  - diagram-list.component.ts: 8 alertas/confirms reemplazados por toasts y diálogo accesible.
  - 
epertoire.component.ts: reemplazados logs por toasts y navegación real.

### Depuración console.*
- **Estado: RESUELTO** — Eliminadas llamadas innecesarias de console.log de depuración en repertorio y administradores.

---

## 7. Plan de Acción y Estado de Resolución

| Item Prioritario | Descripción | Estado P7a |
|---|---|---|
| **P1.1 Shell de Aplicación** | Cabecera + barra lateral colapsable + bottom-nav móvil + notificaciones + menú usuario | **RESUELTO** |
| **P1.2 Estado de Página Reutilizable** | PageStateComponent (loading, empty, error con reintento) | **RESUELTO** |
| **P1.3 Centro de Proyecto** | /projects/:projectId con 5 pestañas (Resumen, Diagramas, Equipo IA, Tareas, Miembros) | **RESUELTO** |
| **P1.4 Flujo de Sesión y 401** | Interceptor con refresh, modal de sesión expirada, guardado de borrador canvas en localStorage, 
eturnUrl | **RESUELTO** |
| **P1.5 Toasts y Confirmaciones** | ToastService y ConfirmDialogService reemplazando todos los lert() y confirm() | **RESUELTO** |
| **P1.6 Acciones Faltantes Backend** | Import/export XMI, historial/restore versiones, perfil, cambio de contraseña, sesiones activas, notificaciones | **RESUELTO** |
| **P2.1 Atajos de Teclado** | Modal de ayuda accesible con tecla ? o botón cabecera | **RESUELTO** |
| **P2.2 Títulos Dinámicos** | Título de pestaña del navegador sincronizado con breadcrumb | **RESUELTO** |
| **P2.3 Auditoría de Usuarios** | Modal de auditoría por usuario en administración | **RESUELTO** |
| **P3.1 Accesibilidad y Performance** | OnPush en nuevos componentes, trackBy en bucles, contraste WCAG AA, skip link | **RESUELTO** |
