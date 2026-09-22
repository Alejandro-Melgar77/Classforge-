import { Component, inject, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SupportTourService } from '../../services/support-tour.service';

@Component({
  selector: 'app-tour-overlay',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './tour-overlay.component.html',
  styleUrls: ['./tour-overlay.component.scss']
})
export class TourOverlayComponent {
  public tourService = inject(SupportTourService);

  // Padding alrededor del elemento iluminado
  readonly padding = 8;

  get rect() {
    return this.tourService.targetRect();
  }

  get step() {
    return this.tourService.currentStep();
  }

  get tour() {
    return this.tourService.activeTour();
  }

  get stepIndex() {
    return this.tourService.currentStepIndex();
  }

  get totalSteps() {
    return this.tour?.steps.length || 0;
  }

  get progress() {
    return this.tourService.progressPercentage();
  }

  get isLastStep(): boolean {
    return this.stepIndex === this.totalSteps - 1;
  }

  // Estilo del Popover según posición calculada
  get popoverStyle(): { [key: string]: string } {
    const r = this.rect;
    if (!r) {
      // Centrado en pantalla si no se encuentra el elemento
      return {
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        position: 'fixed'
      };
    }

    const pos = this.step?.position || 'bottom';
    const popoverWidth = 340;
    const offset = 14;

    let top = 0;
    let left = 0;

    switch (pos) {
      case 'bottom':
        top = r.bottom + offset;
        left = Math.max(16, Math.min(window.innerWidth - popoverWidth - 16, r.left + (r.width / 2) - (popoverWidth / 2)));
        break;
      case 'top':
        top = Math.max(16, r.top - offset - 200);
        left = Math.max(16, Math.min(window.innerWidth - popoverWidth - 16, r.left + (r.width / 2) - (popoverWidth / 2)));
        break;
      case 'right':
        top = Math.max(16, r.top + (r.height / 2) - 100);
        left = r.right + offset;
        if (left + popoverWidth > window.innerWidth) {
          left = r.left - popoverWidth - offset;
        }
        break;
      case 'left':
        top = Math.max(16, r.top + (r.height / 2) - 100);
        left = Math.max(16, r.left - popoverWidth - offset);
        break;
      case 'center':
      default:
        return {
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          position: 'fixed'
        };
    }

    return {
      top: `${top}px`,
      left: `${left}px`,
      position: 'fixed',
      width: `${popoverWidth}px`
    };
  }

  @HostListener('window:keydown.escape')
  onEscape() {
    this.tourService.endTour();
  }

  next() {
    this.tourService.nextStep();
  }

  prev() {
    this.tourService.previousStep();
  }

  skip() {
    this.tourService.endTour();
  }
}
