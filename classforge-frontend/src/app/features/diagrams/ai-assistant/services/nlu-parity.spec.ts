import { TestBed } from '@angular/core/testing';
import { NluParserService } from './nlu-parser.service';
import nluCases from '../../../../../../../shared/nlu_cases.json';

describe('Cross-Platform NLU Parity Tests (shared/nlu_cases.json)', () => {
  let service: NluParserService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [NluParserService]
    });
    service = TestBed.inject(NluParserService);
  });

  it('debe cargar al menos 15 casos de paridad desde shared/nlu_cases.json', () => {
    expect(nluCases.length).toBeGreaterThanOrEqual(15);
  });

  it('TypeScript NluParserService debe satisfacer los casos de paridad compartidos', () => {
    for (const testCase of nluCases) {
      const prompt = testCase.prompt;
      const acceptedActions = testCase.accepted_actions || [testCase.expected_action];

      const result = service.parse(prompt);
      expect(result).toBeTruthy();

      // Action alignment
      expect(acceptedActions).withContext(`Prompt: "${prompt}" - acción "${result.action}" no está en ${acceptedActions.join(', ')}`).toContain(result.action);

      // Expected classes
      if (testCase.expected_classes && testCase.expected_classes.length > 0) {
        const resultClassNames = (result.classes || []).map(c => c.name.toLowerCase());
        for (const expCls of testCase.expected_classes) {
          expect(resultClassNames).withContext(`Prompt: "${prompt}" - clase "${expCls}" no encontrada en ${resultClassNames.join(', ')}`).toContain(expCls.toLowerCase());
        }
      }

      // Expected relations
      if ('expected_relation' in testCase && testCase.expected_relation) {
        const expRel = testCase.expected_relation;
        expect(result.relations && result.relations.length > 0).withContext(`Prompt: "${prompt}" - se esperaba relación`).toBeTrue();
        if (result.relations && result.relations.length > 0) {
          const rel = result.relations[0];
          expect(rel.type.toLowerCase()).withContext(`Prompt: "${prompt}" - tipo relación mismatch`).toBe(expRel.type.toLowerCase());
          expect(rel.source.toLowerCase()).toBe(expRel.source.toLowerCase());
          expect(rel.target.toLowerCase()).toBe(expRel.target.toLowerCase());
        }
      }

      // Expected deleted
      if ('expected_deleted' in testCase && testCase.expected_deleted) {
        const resultDeleted = ((result as any).deleted_elements || (result as any).deletedElements || []).map((d: string) => d.toLowerCase());
        for (const expDel of testCase.expected_deleted) {
          expect(resultDeleted).withContext(`Prompt: "${prompt}" - elemento eliminado "${expDel}" no encontrado`).toContain(expDel.toLowerCase());
        }
      }
    }
  });
});
