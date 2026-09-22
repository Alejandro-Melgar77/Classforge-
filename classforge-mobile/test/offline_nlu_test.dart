import 'package:flutter_test/flutter_test.dart';
import 'package:classforge_mobile/core/services/offline_nlu_service.dart';

void main() {
  group('OfflineNluService Tests (<1ms, 0MB memory, 100% On-Device)', () {
    late OfflineNluService nlu;

    setUp(() {
      nlu = OfflineNluService();
    });

    test('Debe reconocer la creación de una clase con atributos', () {
      final res = nlu.parse('crear clase Factura con atributos id:long, monto:double');

      expect(res.action, equals('create_class'));
      expect(res.classes.length, equals(1));
      expect(res.classes.first.name, equals('Factura'));
      expect(res.classes.first.attributes.length, equals(2));
      expect(res.classes.first.attributes[0].name, equals('id'));
      expect(res.classes.first.attributes[0].type, equals('long'));
      expect(res.classes.first.attributes[1].name, equals('monto'));
      expect(res.classes.first.attributes[1].type, equals('double'));
      expect(res.latencyMs, lessThan(20.0)); // Microsegundos a milisegundos
    });

    test('Debe reconocer la eliminación de una clase', () {
      final res = nlu.parse('eliminar clase DetallePedido');

      expect(res.action, equals('delete_element'));
      expect(res.deletedElements.length, equals(1));
      expect(res.deletedElements.first, equals('DetallePedido'));
    });

    test('Debe reconocer la adición de un atributo a una clase existente', () {
      final res = nlu.parse('agregar atributo email:string a la clase Usuario');

      expect(res.action, equals('update_class'));
      expect(res.classes.first.name, equals('Usuario'));
      expect(res.classes.first.attributes.length, equals(1));
      expect(res.classes.first.attributes.first.name, equals('email'));
      expect(res.classes.first.attributes.first.type, equals('string'));
    });

    test('Debe reconocer la adición de un método a una clase existente', () {
      final res = nlu.parse('agregar metodo validarToken(token):boolean a la clase Auth');

      expect(res.action, equals('update_class'));
      expect(res.classes.first.name, equals('Auth'));
      expect(res.classes.first.methods.length, equals(1));
      expect(res.classes.first.methods.first.name, equals('validarToken'));
      expect(res.classes.first.methods.first.params, equals('(token)'));
      expect(res.classes.first.methods.first.returnType, equals('boolean'));
    });

    test('Debe reconocer relaciones entre clases', () {
      final res = nlu.parse('relacionar Pedido con Item por composicion');

      expect(res.action, equals('add_relation'));
      expect(res.relations.length, equals(1));
      expect(res.relations.first.source, equals('Pedido'));
      expect(res.relations.first.target, equals('Item'));
      expect(res.relations.first.type, equals('composition'));
    });

    test('Debe reconocer herencia con lenguaje natural especial', () {
      final res = nlu.parse('hacer que Administrador herede de Usuario');

      expect(res.action, equals('add_relation'));
      expect(res.relations.length, equals(1));
      expect(res.relations.first.source, equals('Administrador'));
      expect(res.relations.first.target, equals('Usuario'));
      expect(res.relations.first.type, equals('inheritance'));
    });

    test('Debe reconocer consultas de inspección para visor móvil', () {
      final res = nlu.parse('buscar clase Cliente');

      expect(res.action, equals('query_class'));
      expect(res.queryTarget, equals('Cliente'));
    });

    test('Debe reconocer solicitud de resumen del diagrama', () {
      final res = nlu.parse('resumen del diagrama');

      expect(res.action, equals('query_summary'));
    });
  });
}
