/**
 * Canonical UI constants and i18n-ready strings for the "Equipo IA" subsystem.
 * Centralizing all user-facing labels ensures maintainability and accessibility.
 */

export const AI_TEAM_I18N = {
  header: {
    title: 'Equipo IA',
    subtitle: 'Colaboración inteligente en tiempo real',
    participativeLabel: 'IA participativa',
    participativeHelp: 'Permite que los roles de IA intervengan de forma proactiva al detectar cambios o preguntas.',
    participativePassiveHelp: 'Modo pasivo: La IA solo responde cuando tú le consultas explícitamente en el chat.',
    participativeChangedBy: (user: string, time: string) => `Modificado por ${user} • ${time}`,
    participativeDefaultAudit: 'Estado del proyecto sincronizado',
    activeModelBadge: 'Gemini 3.8 Flash',
    activeModelTitle: 'Modelo LLM activo de alta velocidad y razonamiento',
    connection: {
      connected: 'En vivo',
      connecting: 'Conectando...',
      reconnecting: 'Reconectando...',
      polling_fallback: 'Modo sondeo',
      disconnected: 'Sin conexión en vivo'
    },
    consumption: {
      label: 'Consumo diario',
      formatTokens: (tokens: number) => `~${tokens.toLocaleString()} tokens hoy`,
      noUsage: '~0 tokens hoy'
    },
    rolesSectionTitle: 'Roles del equipo de IA',
    autonomyTooltipForbidden: "Solo Scrum Master, Owner o Administrador pueden configurar la autonomía 'Aplicar'.",
    autonomyOptions: {
      suggest: 'Solo sugerir',
      apply: 'Aplicar',
      off: 'Desactivado'
    },
    roleActive: 'Rol activo',
    roleInactive: 'Rol desactivado',
    toggleRole: (role: string, active: boolean) => `${active ? 'Desactivar' : 'Activar'} rol ${role}`,
    setAutonomy: (role: string) => `Configurar nivel de autonomía para ${role}`
  },
  tabs: {
    commands: 'Comandos UML',
    aiTeam: 'Equipo IA',
    chat: 'Chat',
    history: 'Historial',
    tasks: 'Tareas'
  },
  chat: {
    askToPrefix: 'Preguntar a:',
    placeholder: 'Escribe un mensaje o usa @rol para invocar un especialista...',
    send: 'Enviar mensaje',
    sending: 'Enviando...',
    failed: 'Error de envío',
    retry: 'Reintentar',
    codeBlockCopy: 'Copiar código',
    codeBlockCopied: '¡Copiado!',
    proposalsHeader: 'Propuestas de cambios',
    applyProposal: 'Aplicar cambios',
    dismissProposal: 'Descartar',
    viewInCanvas: 'Ver en lienzo',
    undoProposal: 'Deshacer',
    appliedStatus: (user: string, time: string) => `Aplicada por ${user}, ${time}`
  },
  history: {
    title: 'Historial de colaboración',
    filterAll: 'Todos los integrantes',
    onlyProposals: 'Solo propuestas',
    appliedOnly: 'Con cambios aplicados',
    searchPlaceholder: 'Buscar mensajes o decisiones...',
    citeInChat: 'Citar en mi chat',
    loadMore: 'Cargar más mensajes anteriores',
    viewDiagram: 'Ver diagrama asociado',
    groupByMember: 'Por integrante',
    groupByDay: 'Cronológico'
  },
  tasks: {
    title: 'Tablero de Tareas de IA',
    createTask: 'Nueva Tarea',
    emptyTasks: 'No hay tareas asignadas para este proyecto.',
    columns: {
      pending: 'Pendiente',
      in_progress: 'En curso',
      needs_input: 'Necesita datos',
      completed: 'Completada',
      failed: 'Fallida'
    },
    execute: 'Ejecutar',
    retry: 'Reintentar',
    cancel: 'Cancelar',
    viewResult: 'Ver resultado'
  },
  drawer: {
    resizeHandleTitle: 'Arrastra para redimensionar el panel',
    closeAriaLabel: 'Cerrar panel de asistente',
    sizeSmall: 'S',
    sizeMedium: 'M',
    sizeLarge: 'L',
    sizePreset: (size: string) => `Ajustar ancho a tamaño ${size}`
  }
} as const;
