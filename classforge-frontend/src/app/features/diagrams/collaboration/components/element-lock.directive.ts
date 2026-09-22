import { Directive } from '@angular/core';

@Directive({
  selector: '[appElementLock]',
  standalone: true
})
export class ElementLockDirective {
  // Can be used later for native DOM elements if needed
}
