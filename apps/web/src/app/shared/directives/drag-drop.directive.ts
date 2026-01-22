import { Directive, HostListener, HostBinding, output, input, ElementRef, inject } from '@angular/core';

@Directive({
  selector: '[appDragDrop]',
  standalone: true
})
export class DragDropDirective {
  dragData = input<unknown>(null);
  dropZone = input<string>('');
  dropped = output<{ data: unknown; zone: string }>();

  private el = inject(ElementRef);

  @HostBinding('attr.draggable') draggable = true;
  @HostBinding('class.dragging') isDragging = false;
  @HostBinding('class.drag-over') isDragOver = false;

  @HostListener('dragstart', ['$event'])
  onDragStart(event: DragEvent): void {
    this.isDragging = true;
    event.dataTransfer?.setData('text/plain', JSON.stringify(this.dragData()));
    event.dataTransfer!.effectAllowed = 'move';
  }

  @HostListener('dragend')
  onDragEnd(): void {
    this.isDragging = false;
  }

  @HostListener('dragover', ['$event'])
  onDragOver(event: DragEvent): void {
    if (this.dropZone()) {
      event.preventDefault();
      event.dataTransfer!.dropEffect = 'move';
      this.isDragOver = true;
    }
  }

  @HostListener('dragleave')
  onDragLeave(): void {
    this.isDragOver = false;
  }

  @HostListener('drop', ['$event'])
  onDrop(event: DragEvent): void {
    if (this.dropZone()) {
      event.preventDefault();
      this.isDragOver = false;

      const data = event.dataTransfer?.getData('text/plain');
      if (data) {
        try {
          const parsedData = JSON.parse(data);
          this.dropped.emit({ data: parsedData, zone: this.dropZone() });
        } catch {
          console.error('Failed to parse drag data');
        }
      }
    }
  }
}
