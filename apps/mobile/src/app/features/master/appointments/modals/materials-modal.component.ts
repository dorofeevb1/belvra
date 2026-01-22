import { Component, input, output, signal, computed, OnChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ModalComponent } from '../../../../shared/components/modal.component';
import { Appointment, UsedMaterial } from '../../../../core/models';
import { CurrencyRubPipe } from '../../../../shared/pipes/currency-rub.pipe';

interface MaterialInput {
  id: string;
  name: string;
  quantity: number;
  pricePerUnit: number;
}

@Component({
  selector: 'app-materials-modal',
  standalone: true,
  imports: [CommonModule, FormsModule, ModalComponent, CurrencyRubPipe],
  template: `
    <app-modal
      [isOpen]="isOpen()"
      title="Учет материалов"
      size="lg"
      (closeModal)="close.emit()"
    >
      @if (appointment()) {
        <ng-container>
          <div class="modal-content">
            <!-- Service Info -->
            <div class="info-card">
              <div class="info-icon">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path>
                </svg>
              </div>
              <div class="info-content">
                <span class="info-label">{{ appointment()!.serviceName }}</span>
                <span class="info-value">{{ appointment()!.clientName }}</span>
              </div>
            </div>

            <!-- Materials List -->
            <div class="materials-section">
              <div class="section-header">
                <label class="section-label">Использованные материалы</label>
                <button type="button" (click)="addMaterial()" class="add-btn">
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
                  </svg>
                  Добавить
                </button>
              </div>

              <div class="materials-list">
                @for (material of materials(); track material.id; let i = $index) {
                  <div class="material-row">
                    <input
                      type="text"
                      [(ngModel)]="material.name"
                      placeholder="Название материала"
                      class="input material-name"
                    />
                    <div class="material-fields">
                      <div class="field-group">
                        <label class="field-label">Кол-во</label>
                        <input
                          type="number"
                          [(ngModel)]="material.quantity"
                          min="0.1"
                          step="0.1"
                          class="input input-sm"
                        />
                      </div>
                      <div class="field-group">
                        <label class="field-label">Цена/ед</label>
                        <input
                          type="number"
                          [(ngModel)]="material.pricePerUnit"
                          min="0"
                          class="input input-sm"
                        />
                      </div>
                      <div class="field-group">
                        <label class="field-label">Сумма</label>
                        <span class="material-total">
                          {{ (material.quantity * material.pricePerUnit) | currencyRub }}
                        </span>
                      </div>
                      <button
                        type="button"
                        (click)="removeMaterial(i)"
                        class="remove-btn"
                        title="Удалить"
                      >
                        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                        </svg>
                      </button>
                    </div>
                  </div>
                } @empty {
                  <div class="empty-materials">
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"></path>
                    </svg>
                    <span>Добавьте использованные материалы</span>
                  </div>
                }
              </div>
            </div>

            <!-- Total -->
            <div class="total-card">
              <span class="total-label">Итого материалов:</span>
              <span class="total-value">{{ totalCost() | currencyRub }}</span>
            </div>
          </div>
        </ng-container>
      }

      <div modal-footer class="modal-actions">
        <button type="button" (click)="close.emit()" class="btn btn-secondary">
          Отмена
        </button>
        <button type="button" (click)="onSave()" class="btn btn-primary">
          Сохранить
        </button>
      </div>
    </app-modal>
  `,
  styles: [`
    .modal-content {
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }

    .info-card {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.875rem 1rem;
      background: var(--color-surface-secondary);
      border-radius: var(--radius-lg);
    }

    .info-icon {
      width: 40px;
      height: 40px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: var(--color-brand-50);
      color: var(--color-brand-500);
      border-radius: var(--radius-md);
      flex-shrink: 0;
    }

    :host-context(.dark) .info-icon {
      background: rgba(236, 72, 153, 0.15);
    }

    .info-icon svg {
      width: 20px;
      height: 20px;
    }

    .info-content {
      display: flex;
      flex-direction: column;
      gap: 0.125rem;
    }

    .info-label {
      font-size: 0.75rem;
      color: var(--color-text-tertiary);
    }

    .info-value {
      font-size: 0.9375rem;
      font-weight: 500;
      color: var(--color-text-primary);
    }

    /* Materials Section */
    .section-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 0.75rem;
    }

    .section-label {
      font-size: 0.875rem;
      font-weight: 500;
      color: var(--color-text-secondary);
    }

    .add-btn {
      display: inline-flex;
      align-items: center;
      gap: 0.375rem;
      padding: 0.375rem 0.75rem;
      font-size: 0.8125rem;
      font-weight: 500;
      color: var(--color-brand-600);
      background: transparent;
      border: none;
      border-radius: var(--radius-md);
      cursor: pointer;
      transition: all 150ms ease;
    }

    .add-btn:hover {
      background: var(--color-brand-50);
    }

    :host-context(.dark) .add-btn:hover {
      background: rgba(236, 72, 153, 0.1);
    }

    .add-btn svg {
      width: 16px;
      height: 16px;
    }

    /* Materials List */
    .materials-list {
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }

    .material-row {
      padding: 1rem;
      background: var(--color-surface-secondary);
      border-radius: var(--radius-lg);
    }

    .material-name {
      width: 100%;
      margin-bottom: 0.75rem;
    }

    .material-fields {
      display: flex;
      align-items: flex-end;
      gap: 0.75rem;
      flex-wrap: wrap;
    }

    .field-group {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
    }

    .field-label {
      font-size: 0.6875rem;
      font-weight: 500;
      color: var(--color-text-tertiary);
      text-transform: uppercase;
    }

    .input-sm {
      width: 5rem;
      padding: 0.5rem 0.625rem;
      font-size: 0.875rem;
    }

    .material-total {
      display: flex;
      align-items: center;
      height: 38px;
      padding: 0 0.5rem;
      font-size: 0.9375rem;
      font-weight: 600;
      color: var(--color-brand-600);
      min-width: 5rem;
    }

    .remove-btn {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 38px;
      height: 38px;
      color: var(--color-text-tertiary);
      background: transparent;
      border: none;
      border-radius: var(--radius-md);
      cursor: pointer;
      transition: all 150ms ease;
    }

    .remove-btn:hover {
      background: var(--color-error-bg);
      color: var(--color-error);
    }

    .remove-btn svg {
      width: 18px;
      height: 18px;
    }

    /* Empty State */
    .empty-materials {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.5rem;
      padding: 2rem 1rem;
      color: var(--color-text-tertiary);
      font-size: 0.875rem;
      text-align: center;
    }

    .empty-materials svg {
      width: 40px;
      height: 40px;
      opacity: 0.5;
    }

    /* Total Card */
    .total-card {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 1rem 1.25rem;
      background: var(--color-brand-50);
      border-radius: var(--radius-lg);
    }

    :host-context(.dark) .total-card {
      background: rgba(236, 72, 153, 0.15);
    }

    .total-label {
      font-size: 0.9375rem;
      font-weight: 500;
      color: var(--color-text-primary);
    }

    .total-value {
      font-size: 1.25rem;
      font-weight: 700;
      color: var(--color-brand-600);
    }

    /* Modal Actions */
    .modal-actions {
      display: flex;
      justify-content: flex-end;
      gap: 0.75rem;
      padding: 1rem 1.5rem;
      border-top: 1px solid var(--color-border-secondary);
      background: var(--color-bg-secondary);
      margin: 0 -1.5rem -1.5rem -1.5rem;
      border-radius: 0 0 var(--radius-2xl) var(--radius-2xl);
    }

    /* Input styling */
    .input {
      width: 100%;
      padding: 0.625rem 0.875rem;
      font-size: 0.875rem;
      color: var(--color-text-primary);
      background: var(--color-surface-primary);
      border: 1px solid var(--color-border-primary);
      border-radius: var(--radius-md);
      transition: all 150ms ease;
    }

    .input::placeholder {
      color: var(--color-text-tertiary);
    }

    .input:focus {
      outline: none;
      border-color: var(--color-brand-500);
      box-shadow: 0 0 0 3px rgba(236, 72, 153, 0.1);
    }

    @media (max-width: 480px) {
      .material-fields {
        flex-direction: column;
        align-items: stretch;
      }

      .field-group {
        flex-direction: row;
        align-items: center;
        justify-content: space-between;
      }

      .input-sm {
        width: auto;
        flex: 1;
      }

      .material-total {
        justify-content: flex-end;
      }

      .remove-btn {
        position: absolute;
        top: 0.5rem;
        right: 0.5rem;
        width: 32px;
        height: 32px;
      }

      .material-row {
        position: relative;
        padding-top: 2.5rem;
      }
    }
  `]
})
export class MaterialsModalComponent implements OnChanges {
  isOpen = input<boolean>(false);
  appointment = input<Appointment | null>(null);
  close = output<void>();
  save = output<{ materials: UsedMaterial[]; totalCost: number }>();

  materials = signal<MaterialInput[]>([]);

  totalCost = computed(() =>
    this.materials().reduce((sum, m) => sum + (m.quantity * m.pricePerUnit), 0)
  );

  ngOnChanges(): void {
    if (this.isOpen()) {
      const apt = this.appointment();
      if (apt?.usedMaterials?.length) {
        this.materials.set(apt.usedMaterials.map(m => ({
          id: m.materialId,
          name: m.name,
          quantity: m.quantity,
          pricePerUnit: m.totalCost / m.quantity
        })));
      } else {
        this.materials.set([]);
      }
    }
  }

  addMaterial(): void {
    this.materials.update(list => [
      ...list,
      {
        id: `mat-${Date.now()}`,
        name: '',
        quantity: 1,
        pricePerUnit: 0
      }
    ]);
  }

  removeMaterial(index: number): void {
    this.materials.update(list => list.filter((_, i) => i !== index));
  }

  onSave(): void {
    const usedMaterials: UsedMaterial[] = this.materials()
      .filter(m => m.name && m.quantity > 0)
      .map(m => ({
        materialId: m.id,
        name: m.name,
        quantity: m.quantity,
        totalCost: m.quantity * m.pricePerUnit
      }));

    this.save.emit({
      materials: usedMaterials,
      totalCost: this.totalCost()
    });
  }
}
