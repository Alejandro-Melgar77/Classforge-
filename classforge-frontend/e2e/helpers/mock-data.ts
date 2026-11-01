export const MOCK_USER_ALICE = {
  id: 'usr-alice-001',
  name: 'Alice Dev',
  email: 'alice@classforge.io',
  role: 'dev',
  avatar_url: null,
  team_ids: ['team-001']
};

export const MOCK_USER_BOB = {
  id: 'usr-bob-002',
  name: 'Bob Architect',
  email: 'bob@classforge.io',
  role: 'architect',
  avatar_url: null,
  team_ids: ['team-001']
};

export const MOCK_PROJECT = {
  id: 'proj-ecommerce-001',
  name: 'E-Commerce Platform',
  description: 'Sistema integral de comercio electrónico y microservicios',
  status: 'active',
  owner_id: 'usr-alice-001',
  team_id: 'team-001',
  team_name: 'Core Engineering',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString()
};

export const MOCK_DIAGRAM = {
  id: 'diag-orders-001',
  name: 'Diagrama de Ordenes',
  description: 'Modelo de clases UML del módulo de pedidos',
  project_id: 'proj-ecommerce-001',
  team_id: 'team-001',
  team_name: 'Core Engineering',
  member_ids: ['usr-alice-001', 'usr-bob-002'],
  created_by: 'usr-alice-001',
  status: 'active',
  is_public: false,
  version: 2,
  created_at: new Date(Date.now() - 3600000).toISOString(),
  updated_at: new Date().toISOString(),
  graph_data: {
    nodes: [
      {
        id: 'node-order',
        type: 'class',
        position: { x: 100, y: 120 },
        size: { width: 220, height: 160 },
        data: {
          name: 'Order',
          stereotype: null,
          attributes: [
            { name: 'id', type: 'UUID', visibility: '+' },
            { name: 'totalAmount', type: 'BigDecimal', visibility: '-' },
            { name: 'status', type: 'OrderStatus', visibility: '+' }
          ],
          methods: [
            { name: 'calculateTotal', returnType: 'BigDecimal', visibility: '+' },
            { name: 'cancel', returnType: 'void', visibility: '+' }
          ],
          notes: null
        }
      },
      {
        id: 'node-customer',
        type: 'class',
        position: { x: 440, y: 120 },
        size: { width: 220, height: 140 },
        data: {
          name: 'Customer',
          stereotype: null,
          attributes: [
            { name: 'id', type: 'UUID', visibility: '+' },
            { name: 'email', type: 'String', visibility: '-' }
          ],
          methods: [
            { name: 'placeOrder', returnType: 'Order', visibility: '+' }
          ],
          notes: null
        }
      }
    ],
    edges: [
      {
        id: 'edge-order-customer',
        type: 'association',
        source: 'node-order',
        target: 'node-customer',
        sourceMultiplicity: '1',
        targetMultiplicity: '1..*'
      }
    ],
    viewport: { x: 0, y: 0, zoom: 1 }
  }
};

export const MOCK_HISTORY_ENTRIES = [
  {
    version: 1,
    saved_by: 'Alice Dev',
    saved_at: new Date(Date.now() - 7200000).toISOString(),
    comment: 'Creación inicial del esquema de órdenes'
  },
  {
    version: 2,
    saved_by: 'Bob Architect',
    saved_at: new Date(Date.now() - 3600000).toISOString(),
    comment: 'Agregada entidad Customer y relación con Order'
  }
];

export const MOCK_AI_TEAM_STATE = {
  project_id: 'proj-ecommerce-001',
  participative: {
    enabled: true,
    updated_by: 'usr-bob-002',
    updated_at: new Date().toISOString()
  },
  roles: [
    {
      role_id: 'architect',
      label: 'Arquitecto de Software',
      emoji: '🏛️',
      description: 'Especialista en diseño y arquitectura de software',
      is_active: true,
      autonomy: 'suggest',
      skin: { primary_color: '#8B5CF6' }
    },
    {
      role_id: 'qa',
      label: 'QA Engineer',
      emoji: '🧪',
      description: 'Especialista en pruebas y calidad',
      is_active: true,
      autonomy: 'suggest',
      skin: { primary_color: '#10B981' }
    }
  ],
  tasks: [],
  unread: { personal: 0, project: 0 }
};

export const MOCK_AI_PROPOSAL = {
  action: 'modify_diagram',
  explanation: 'El Arquitecto propone agregar la clase Payment para desacoplar el procesamiento de pagos.',
  classes: [
    {
      name: 'Payment',
      stereotype: 'service',
      attributes: [
        { name: 'paymentId', type: 'String', visibility: '+' },
        { name: 'amount', type: 'BigDecimal', visibility: '-' },
        { name: 'paymentMethod', type: 'String', visibility: '+' }
      ],
      methods: [
        { name: 'processPayment', return_type: 'boolean', params: 'token', visibility: '+' }
      ]
    }
  ],
  relations: [
    {
      source: 'Order',
      target: 'Payment',
      type: 'composition',
      sourceMultiplicity: '1',
      targetMultiplicity: '1..*'
    }
  ],
  deleted_elements: []
};
