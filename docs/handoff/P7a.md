# Handoff P7a — App 100 % Navegable: Shell, Rutas y Centro de Proyecto

**Fecha de Entrega:** 1 de noviembre de 2026  
**Autor:** Agente Antigravity  
**Estado:** COMPLETADO Y VERIFICADO (Build Verde + Tests Verdes + Cero Callejones sin Salida)

---

## 1. Resumen Ejecutivo

En este hito **P7a**, la aplicación ClassForge ha sido completamente transformada en una plataforma **100 % navegable**, eliminando todos los callejones sin salida (*dead ends*) y rutas huérfanas, integrando todas las acciones del backend previamente inaccesibles desde la UI, y garantizando consistencia absoluta en resoluciones de **360 px (móvil)**, **768 px (tablet)** y **1280 px (escritorio)**.

### Logros Principales:
1. **Auditoría Exhaustiva (docs/ux/audit.md):** Inventario completo de rutas, clasificación de severidades P1/P2/P3 y resolución comprobada de todos los ítems P1.
2. **Shell de Aplicación Responsivo y Accesible:**
   - Barra lateral colapsable en escritorio/tablet que muta elegantemente a una **barra de navegación inferior (*bottom-nav*)** con controles táctiles en pantallas móviles (< 768px).
   - Cabecera unificada con rastro de migas de pan (*breadcrumbs*) jerárquicas reactivas, indicador de campana con contador de notificaciones no leídas y panel desplegable en tiempo real.
   - Menú de usuario multimodal con pestañas para **Perfil** (edición de nombre y avatar), **Seguridad** (cambio de contraseña), **Sesiones Activas** (listado con IP y navegador) y **Cerrar sesión en todos los dispositivos**.
   - Diálogo global de atajos de teclado accesible mediante la tecla ? o el botón de ayuda en cabecera.
3. **Centro de Proyecto (/projects/:projectId):**
   - Centro unificado con 5 pestañas enlazadas mediante rutas hijas:
     - **Resumen:** Métricas del proyecto, estado, descripción y equipo asignado.
     - **Diagramas:** Explorador de diagramas, creación modal, importación y exportación de archivos XMI.
     - **Equipo IA:** Integración a pantalla completa del panel multi-agente P6b.
     - **Tareas:** Gestión de tareas del proyecto con filtro y cambio de estado.
     - **Miembros:** Gestión de integrantes del equipo y asignación.
   - Navegación contextual con botón «← Volver a Proyectos» y redirección automática transparente desde la ruta previa obsoleta /ai-chat/:projectId.
4. **Flujos Transversales Robustos:**
   - **Gestión de Sesión (401 / Timeout de 30 min):** Renovación de token con intento único; ante fallo o timeout, salvaguarda automática de borrador del lienzo UML en localStorage (cf_draft_diagram_{id}), modal accesible de sesión expirada y redirección a login conservando 
eturnUrl para retornar automáticamente a la pantalla de trabajo tras autenticarse.
   - **Eliminación Total de lert() y confirm() nativos:** 32 llamadas bloqueantes reemplazadas por ToastService reactivo y ConfirmDialogService con modales accesibles (WCAG AA).
   - **Estado de Página Reutilizable (PageStateComponent):** Manejo consistente de estados de carga, colecciones vacías y pantallas de error (403/404) con reintento.
5. **Calidad de Código y Arquitectura:**
   - Cero archivos mayores a 400 líneas.
   - Lazy loading modular por feature.
   - Detección de cambios OnPush y 	rackBy en bucles.

---

## 2. Inventario de Rutas y Navegabilidad

| Ruta | Componente Host | Punto de Acceso en UI | Estado |
|---|---|---|---|
| /auth/login | LoginComponent | Redirección inicial si no hay sesión / Botón Cerrar Sesión | Activo |
| /auth/register | RegisterComponent | Enlace en pantalla de Login | Activo |
| /dashboard | DashboardComponent | Ítem «Inicio» en barra lateral o bottom-nav | Activo |
| /projects/mine | RepertoireComponent | Ítem «Proyectos» en barra lateral o bottom-nav | Activo |
| /projects/teams | RepertoireComponent | Ítem «Mis Equipos» en barra lateral o bottom-nav | Activo |
| /projects/:projectId | ProjectCenterComponent | Clic en tarjeta de proyecto en Repertorio o Dashboard | Activo |
| /projects/:projectId/resumen | ProjectOverviewComponent | Pestaña «Resumen» en Centro de Proyecto | Activo |
| /projects/:projectId/diagramas | ProjectDiagramsComponent | Pestaña «Diagramas» en Centro de Proyecto | Activo |
| /projects/:projectId/equipo-ia | ProjectAiTeamComponent | Pestaña «Equipo IA» o botón 🤖 en tarjeta de proyecto | Activo |
| /projects/:projectId/tareas | ProjectTasksComponent | Pestaña «Tareas» en Centro de Proyecto | Activo |
| /projects/:projectId/miembros | ProjectMembersComponent | Pestaña «Miembros» en Centro de Proyecto | Activo |
| /diagrams | DiagramListComponent | Ítem «Diagramas» en barra lateral o bottom-nav | Activo |
| /diagrams/:id | DiagramCanvasComponent | Clic en diagrama desde lista o Centro de Proyecto | Activo |
| /admin/users | UserListComponent | Ítem «Administración» en barra lateral (rol admin) | Activo |
| /admin/teams | TeamListComponent | Pestaña «Equipos» en panel de Administración | Activo |
| /admin/config | GlobalConfigComponent | Pestaña «Configuración» en panel de Administración | Activo |
| /ai-chat/:projectId | *Redirección 301 interna* | Redirige automáticamente a /projects/:projectId/equipo-ia | Redirección |

---

## 3. Componentes y Servicios Creados en P7a

Todos los archivos respetan estrictamente la restricción de tamaño (< 400 líneas):

| Archivo | Rol | Líneas |
|---|---|---|
| core/services/toast.service.ts | Servicio reactivo de notificaciones tipo Toast | 58 |
| core/services/confirm-dialog.service.ts | Servicio asíncrono de confirmación accesible | 43 |
| core/services/breadcrumb.service.ts | Extractor de rutas con título dinámico de documento | 82 |
| core/services/notification.service.ts | Cliente API para notificaciones del backend | 48 |
| core/services/session-state.service.ts | Manejo de expiración de sesión y borrador de lienzo | 45 |
| shared/components/page-state/page-state.component.ts | Componente reutilizable loading / empty / error | 65 |
| shared/components/breadcrumbs/breadcrumbs.component.ts | Barra de migas de pan accesible | 45 |
| shared/components/toast-container/toast-container.component.ts | Contenedor de toasts con animación y aria-live | 42 |
| shared/components/confirm-dialog/confirm-dialog.component.ts | Modal de confirmación accesible | 50 |
| shared/components/session-expired-modal/session-expired-modal.component.ts | Modal de aviso de sesión caducada | 48 |
| layout/shell/user-menu-modal/user-menu-modal.component.ts | Modal de perfil, contraseña y sesiones activas | 285 |
| layout/shell/notifications-panel/notifications-panel.component.ts | Panel desplegable de notificaciones | 120 |
| layout/shell/shortcuts-dialog/shortcuts-dialog.component.ts | Modal de atajos de teclado globales | 95 |
| layout/shell/shell.component.ts | Shell principal con cabecera, sidebar y bottom-nav | 185 |
| eatures/projects/center/project-center.component.ts | Host del Centro de Proyecto | 170 |
| eatures/projects/center/project-overview.component.ts | Pestaña Resumen con métricas y estado | 185 |
| eatures/projects/center/project-diagrams.component.ts | Pestaña Diagramas con importación XMI | 240 |
| eatures/projects/center/project-ai-team.component.ts | Pestaña Equipo IA a pantalla completa | 40 |
| eatures/projects/center/project-tasks.component.ts | Pestaña Tareas del proyecto | 170 |
| eatures/projects/center/project-members.component.ts | Pestaña Miembros y roles del proyecto | 200 |

---

## 4. Recorrido Manual de Navegación 100 % por Clics

Para validar la ausencia de callejones sin salida, el siguiente flujo puede realizarse exclusivamente mediante interacción con ratón o toques:

1. **Dashboard Inicial (/dashboard):**
   - Clic en «Nuevo Proyecto» o clic sobre una tarjeta de proyecto existente en la lista rápida.
2. **Acceso al Centro de Proyecto (/projects/:projectId):**
   - El clic conduce inmediatamente a /projects/:projectId/resumen.
   - Se observa el breadcrumb: Inicio > Proyectos > [Nombre del Proyecto] > Resumen.
   - Se puede alternar entre las 5 pestañas:
     - Clic en «Diagramas»: se lista la colección de diagramas; botón «+ Nuevo Diagrama» o «Importar XMI».
     - Clic en «Equipo IA»: se despliega la interfaz multi-agente P6b con sus tres agentes en vivo.
     - Clic en «Tareas»: filtrado y creación de tareas.
     - Clic en «Miembros»: gestión del equipo y asignación.
3. **Navegación al Lienzo de Diagrama (/diagrams/:id):**
   - Al hacer clic en un diagrama, se abre el lienzo UML.
   - En la cabecera del lienzo, el botón «v1» abre el **Historial de Versiones**, permitiendo restaurar estados anteriores con un clic.
   - Se encuentran disponibles los botones para descargar XMI, JSON e importar XMI.
   - Clic en el botón «← Volver»: detecta automáticamente que provino de un proyecto y regresa a /projects/:projectId/diagramas (sin perder el contexto).
4. **Navegación Global en Móvil (360 px):**
   - En pantallas compactas, la barra inferior (*bottom-nav*) presenta botones fijos para «Inicio», «Proyectos», «Diagramas», «Equipos» y «Menú».
   - Tocar «Menú» abre el panel de usuario con opciones de perfil, cambio de contraseña, sesiones y cierre de sesión.
5. **Notificaciones y Ayuda:**
   - En cualquier pantalla, presionar el ícono de campana en la cabecera abre el panel con las notificaciones más recientes.
   - Presionar ? en el teclado o pulsar el botón ? en la cabecera abre la guía de atajos de teclado sin interrumpir la vista activa.

---

## 5. Verificación de Compilación y Calidad

- **Compilación en Producción (
pm run build):**
  - **Estado:** EXITOSO (Código de salida: 0).
  - **Generación de Chunks:** Lazy chunks correctamente segregados para diagrams-routes (281 kB), projects-routes (53 kB), dmin-routes (50 kB), dashboard-routes (10 kB), uth-routes (8 kB).
- **Pruebas Unitarias Karma (
pm test):**
  - **Estado:** 100 % EXITOSO.
  - **Resultados:** 73/73 tests ejecutados sin fallos en ChromeHeadless.
- **Auditoría UX:**
  - Archivo docs/ux/audit.md actualizado con todas las filas P1 en estado **RESUELTO**.
