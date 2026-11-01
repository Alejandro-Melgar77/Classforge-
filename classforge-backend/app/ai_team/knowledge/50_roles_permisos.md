# 50 — Roles, Permisos y Gobernanza en ClassForge

ClassForge implementa un modelo de seguridad por capas que gobierna tanto a los usuarios humanos como a los agentes de IA dentro de los proyectos.

## 1. Roles de Usuarios Humanos (`app/modules/users/models.py`)

- **`admin`**: Administrador del sistema. Posee acceso global irrestricto a todos los proyectos, equipos, diagramas y endpoints administrativos restringidos (ej. `GET /api/v1/ai-chat/knowledge/manifest`).
- **`scrum_master`**: Líder técnico y de gestión. Crea y administra equipos ágiles (`teams`), proyectos (`projects`), aprueba decisiones de diseño y asigna tareas autónomas a los roles de IA.
- **`developer` (`dev`)**: Desarrollador del equipo. Crea diagramas personales y colabora activamente en los diagramas de su equipo asignado, interactúa con el chat de IA y genera código backend.

## 2. Políticas de Autorización Puras (`app/core/authz.py`)

El acceso a los recursos se decide mediante funciones puras desacopladas de frameworks:
- **`can_access_project(user, project, team)`**:
  - Concede acceso si:
    1. El usuario tiene rol `admin`.
    2. El usuario es el propietario directo (`owner_id`).
    3. El usuario es Scrum Master del equipo del proyecto.
    4. El usuario es miembro activo (`member_ids`) del equipo asignado.
- **`can_access_diagram(user, diagram, team, project)`**:
  - Concede acceso si el usuario es `admin`, creador del diagrama, miembro listado en `member_ids`, o si posee acceso legítimo al proyecto contenedor.

## 3. Roles de Inteligencia Artificial (`app/ai_team/domain/roles.py`)

El equipo de IA se compone de personas especializadas que participan en el chat grupal (`/api/v1/ai-chat/projects/{id}/messages`):
- **Arquitecto (`architect`)**: Evalúa modularidad, cohesión, acoplamiento, límites de agregados y cumplimiento de SOLID.
- **Analista de Calidad (`qa`)**: Identifica inconsistencias, reglas violadas del linter, nombres no estandarizados y cardinalidades contradictorias.
- **Tech Lead (`tech_lead`)**: Evalúa la viabilidad técnica para codegen (Spring Boot / FastAPI), sugiere patrones prácticos y estándares de codificación.
- **Mentor / Tutor (`mentor`)**: Enseña conceptos de modelado UML y POO mediante explicaciones pedagógicas claras y analogías.
- **DBA / Persistencia (`dba`)**: Revisa claves primarias, foráneas, normalización de datos relacionales y tipos adecuados para bases de datos.
- **Seguridad (`security`)**: Revisa consideraciones OWASP, no almacenamiento de credenciales en texto plano, y roles/permisos dentro del dominio.
- **Analista Funcional (`analyst`)**: Traduce requisitos de negocio e historias de usuario a clasificadores y relaciones en el diagrama.

Todos los roles emiten propuestas tipadas en el contrato unificado `AiTeamResponse`, permitiendo que el equipo humano revise, apruebe o descarte cambios antes de que afecten el lienzo.
