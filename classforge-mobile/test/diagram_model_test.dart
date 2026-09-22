import 'package:flutter_test/flutter_test.dart';
import 'package:classforge_mobile/models/diagram_model.dart';
import 'package:classforge_mobile/models/notification_model.dart';

void main() {
  group('DiagramModel & NotificationModel Tests', () {
    test('Debe deserializar correctamente un diagrama UML completo con nodos y aristas', () {
      final json = {
        'id': 'diag-123',
        'name': 'Diagrama de Comercio',
        'description': 'Arquitectura de ordenes',
        'project_id': 'proj-999',
        'status': 'in_progress',
        'version': 3,
        'graph_data': {
          'nodes': [
            {
              'id': 'node-1',
              'type': 'uml-class',
              'position': {'x': 100.0, 'y': 150.0},
              'size': {'width': 220.0, 'height': 160.0},
              'data': {
                'name': 'Orden',
                'stereotype': 'entity',
                'attributes': [
                  {'visibility': '+', 'name': 'id', 'type': 'Long'},
                  {'visibility': '-', 'name': 'fecha', 'type': 'LocalDateTime'},
                  '+ total: Double'
                ],
                'methods': [
                  {'visibility': '+', 'name': 'calcularTotal', 'params': '()', 'return_type': 'Double'},
                  '+ procesar(): Boolean'
                ]
              }
            },
            {
              'id': 'node-2',
              'type': 'uml-interface',
              'position': {'x': 400.0, 'y': 150.0},
              'size': {'width': 200.0, 'height': 120.0},
              'data': {
                'name': 'IPagoService',
                'stereotype': 'interface',
                'attributes': [],
                'methods': [
                  {'visibility': '+', 'name': 'procesarPago', 'params': '(monto: Double)', 'return_type': 'String'}
                ]
              }
            }
          ],
          'edges': [
            {
              'id': 'edge-1',
              'type': 'uml-composition',
              'source': {'cell': 'node-1'},
              'target': {'cell': 'node-2'},
              'label': '1..*'
            }
          ]
        }
      };

      final diagram = DiagramModel.fromJson(json);

      expect(diagram.id, equals('diag-123'));
      expect(diagram.name, equals('Diagrama de Comercio'));
      expect(diagram.version, equals(3));
      expect(diagram.nodes.length, equals(2));
      expect(diagram.edges.length, equals(1));

      // Node 1 checks
      final node1 = diagram.nodes[0];
      expect(node1.id, equals('node-1'));
      expect(node1.name, equals('Orden'));
      expect(node1.type, equals('class'));
      expect(node1.x, equals(100.0));
      expect(node1.y, equals(150.0));
      expect(node1.attributes.length, equals(3));
      expect(node1.attributes[0].name, equals('id'));
      expect(node1.attributes[2].name, equals('total'));
      expect(node1.methods.length, equals(2));

      // Node 2 checks
      final node2 = diagram.nodes[1];
      expect(node2.id, equals('node-2'));
      expect(node2.name, equals('IPagoService'));
      expect(node2.type, equals('interface'));

      // Edge checks
      final edge1 = diagram.edges[0];
      expect(edge1.id, equals('edge-1'));
      expect(edge1.type, equals('composition'));
      expect(edge1.sourceId, equals('node-1'));
      expect(edge1.targetId, equals('node-2'));
      expect(edge1.label, equals('1..*'));
    });

    test('Debe deserializar InAppNotificationModel con icono y estado de lectura', () {
      final notifJson = {
        'id': 'notif-1',
        'title': 'Diagrama Actualizado',
        'message': 'Se añadió la clase Usuario al diagrama',
        'type': 'diagram_modified',
        'timestamp': '2026-09-07T14:30:00Z',
        'diagram_id': 'diag-123',
        'is_read': false
      };

      final notif = InAppNotificationModel.fromJson(notifJson);

      expect(notif.id, equals('notif-1'));
      expect(notif.title, equals('Diagrama Actualizado'));
      expect(notif.type, equals('diagram_modified'));
      expect(notif.typeIcon, equals('✏️'));
      expect(notif.isRead, isFalse);
      expect(notif.diagramId, equals('diag-123'));
    });
  });
}
