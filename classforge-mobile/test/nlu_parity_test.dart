import 'dart:convert';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:classforge_mobile/core/services/offline_nlu_service.dart';

void main() {
  group('Cross-Platform NLU Parity Tests (shared/nlu_cases.json)', () {
    late OfflineNluService nlu;
    late List<dynamic> cases;

    setUpAll(() {
      nlu = OfflineNluService();
      // Locate shared/nlu_cases.json relative to classforge-mobile
      final possiblePaths = [
        '../shared/nlu_cases.json',
        'shared/nlu_cases.json',
        '../../shared/nlu_cases.json',
      ];
      File? file;
      for (final p in possiblePaths) {
        final f = File(p);
        if (f.existsSync()) {
          file = f;
          break;
        }
      }
      expect(file, isNotNull, reason: 'shared/nlu_cases.json must exist');
      cases = jsonDecode(file!.readAsStringSync()) as List<dynamic>;
    });

    test('Debe cargar al menos 15 casos de paridad', () {
      expect(cases.length, greaterThanOrEqualTo(15));
    });

    test('Dart OfflineNluService debe cumplir con las fixtures compartidas', () {
      for (final caseData in cases) {
        final map = caseData as Map<String, dynamic>;
        final prompt = map['prompt'] as String;
        final acceptedActions = (map['accepted_actions'] as List<dynamic>).map((e) => e.toString()).toList();

        final result = nlu.parse(prompt);

        // Action alignment
        expect(
          acceptedActions.contains(result.action),
          isTrue,
          reason: "Prompt '$prompt': acción '${result.action}' no está en $acceptedActions",
        );

        // Class name verification
        if (map.containsKey('expected_classes')) {
          final expectedClasses = (map['expected_classes'] as List<dynamic>).map((e) => e.toString().toLowerCase()).toList();
          if (expectedClasses.isNotEmpty) {
            final resultClasses = result.classes.map((c) => c.name.toLowerCase()).toList();
            for (final expCls in expectedClasses) {
              expect(
                resultClasses.contains(expCls),
                isTrue,
                reason: "Prompt '$prompt': clase esperada '$expCls' no encontrada en $resultClasses",
              );
            }
          }
        }

        // Relation verification
        if (map.containsKey('expected_relation')) {
          final expRel = map['expected_relation'] as Map<String, dynamic>;
          expect(result.relations.isNotEmpty, isTrue, reason: "Prompt '$prompt': se esperaba relación");
          final rel = result.relations.first;
          expect(
            rel.type.toLowerCase(),
            equals((expRel['type'] as String).toLowerCase()),
            reason: "Prompt '$prompt': tipo de relación mismatch",
          );
          expect(
            rel.source.toLowerCase(),
            equals((expRel['source'] as String).toLowerCase()),
          );
          expect(
            rel.target.toLowerCase(),
            equals((expRel['target'] as String).toLowerCase()),
          );
        }

        // Deleted elements
        if (map.containsKey('expected_deleted')) {
          final expDel = (map['expected_deleted'] as List<dynamic>).map((e) => e.toString().toLowerCase()).toList();
          final resDel = result.deletedElements.map((e) => e.toLowerCase()).toList();
          for (final del in expDel) {
            expect(resDel.contains(del), isTrue, reason: "Prompt '$prompt': elemento eliminado no encontrado");
          }
        }
      }
    });
  });
}
