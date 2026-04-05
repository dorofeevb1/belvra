import { Component, input, output, inject, signal, OnChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ModalComponent } from '../../../shared/components/modal.component';
import { AuthService, DataService, AIService, NotificationService } from '../../../core/services';
import { PortfolioItem, BeautyService } from '../../../core/models';

@Component({
  selector: 'app-portfolio-item-modal',
  standalone: true,
  imports: [CommonModule, FormsModule, ModalComponent],
  template: `
    <app-modal
      [isOpen]="isOpen()"
      [title]="editItem() ? 'Редактировать работу' : 'Новая работа'"
      size="lg"
      (closeModal)="close.emit()"
    >
      <div class="modal-content">
        <!-- Image Upload -->
        <div class="form-group">
          <label class="form-label">Изображение</label>
          @if (imagePreview()) {
            <div class="image-preview">
              <img [src]="imagePreview()" alt="Preview" />
              <button type="button" (click)="removeImage()" class="remove-image-btn">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
              </button>
            </div>
          } @else {
            <label class="upload-area">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
              </svg>
              <span>Нажмите для загрузки</span>
              <input
                type="file"
                accept="image/*"
                (change)="onFileSelected($event)"
                class="hidden-input"
              />
            </label>
          }
        </div>

        <!-- AI Generate Button -->
        @if (imagePreview()) {
          <button
            type="button"
            (click)="generateWithAI()"
            [disabled]="isGenerating()"
            class="ai-btn"
          >
            @if (isGenerating()) {
              <svg class="spinner-icon" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <span>Генерация...</span>
            } @else {
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
              </svg>
              <span>Сгенерировать с ИИ</span>
            }
          </button>
        }

        <!-- Title -->
        <div class="form-group">
          <label class="form-label">Название</label>
          <input
            type="text"
            [(ngModel)]="title"
            placeholder="Название работы"
            class="input"
          />
        </div>

        <!-- Description -->
        <div class="form-group">
          <label class="form-label">Описание</label>
          <textarea
            [(ngModel)]="description"
            rows="3"
            placeholder="Описание работы"
            class="input textarea"
          ></textarea>
        </div>

        <!-- Hashtags -->
        <div class="form-group">
          <label class="form-label">Хештеги</label>
          <input
            type="text"
            [(ngModel)]="hashtagsInput"
            (input)="updateParsedHashtags()"
            placeholder="Введите хештеги через запятую"
            class="input"
          />
          @if (parsedHashtags().length > 0) {
            <div class="hashtags-preview">
              @for (tag of parsedHashtags(); track tag) {
                <span class="hashtag">#{{ tag }}</span>
              }
            </div>
          }
        </div>

        <!-- Service -->
        <div class="form-group">
          <label class="form-label">Связанная услуга</label>
          <select [(ngModel)]="selectedServiceId" class="input select">
            <option value="">Не выбрана</option>
            @for (service of services(); track service.id) {
              <option [value]="service.serviceId || ''">{{ service.name }}</option>
            }
          </select>
        </div>
      </div>

      <div modal-footer class="modal-actions">
        <button type="button" (click)="close.emit()" class="btn btn-secondary">
          Отмена
        </button>
        <button
          type="button"
          (click)="onSave()"
          [disabled]="!isValid()"
          class="btn btn-primary"
        >
          {{ editItem() ? 'Сохранить' : 'Добавить' }}
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

    .form-group {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }

    .form-label {
      font-size: 0.875rem;
      font-weight: 500;
      color: var(--color-text-secondary);
    }

    /* Image Upload */
    .image-preview {
      position: relative;
      aspect-ratio: 16 / 9;
      border-radius: var(--radius-lg);
      overflow: hidden;
      background: var(--color-surface-secondary);
    }

    .image-preview img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }

    .remove-image-btn {
      position: absolute;
      top: 0.5rem;
      right: 0.5rem;
      width: 32px;
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(0, 0, 0, 0.7);
      border: 2px solid rgba(255, 255, 255, 0.3);
      border-radius: var(--radius-full);
      box-shadow: var(--shadow-md);
      cursor: pointer;
      transition: all 150ms ease;
    }

    .remove-image-btn:hover {
      background: #dc2626;
      border-color: #dc2626;
      transform: scale(1.1);
    }

    .remove-image-btn svg {
      width: 16px;
      height: 16px;
      color: white;
      stroke: white;
    }

    .upload-area {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      aspect-ratio: 16 / 9;
      border: 2px dashed var(--color-border-primary);
      border-radius: var(--radius-lg);
      cursor: pointer;
      transition: all 150ms ease;
      gap: 0.5rem;
      color: var(--color-text-tertiary);
    }

    .upload-area:hover {
      border-color: var(--color-brand-500);
      color: var(--color-brand-500);
    }

    .upload-area svg {
      width: 40px;
      height: 40px;
      opacity: 0.7;
    }

    .upload-area span {
      font-size: 0.875rem;
    }

    .hidden-input {
      display: none;
    }

    /* AI Button */
    .ai-btn {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
      width: 100%;
      padding: 0.75rem 1rem;
      font-size: 0.875rem;
      font-weight: 500;
      color: white;
      background: linear-gradient(135deg, #8b5cf6, var(--color-brand-500));
      border: none;
      border-radius: var(--radius-lg);
      cursor: pointer;
      transition: all 150ms ease;
    }

    .ai-btn:hover:not(:disabled) {
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(139, 92, 246, 0.4);
    }

    .ai-btn:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }

    .ai-btn svg {
      width: 20px;
      height: 20px;
    }

    .spinner-icon {
      animation: spin 0.7s linear infinite;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    /* Inputs */
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

    .textarea {
      resize: none;
      min-height: 5rem;
    }

    .select {
      appearance: none;
      background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e");
      background-position: right 0.5rem center;
      background-repeat: no-repeat;
      background-size: 1.5em 1.5em;
      padding-right: 2.5rem;
    }

    /* Hashtags */
    .hashtags-preview {
      display: flex;
      flex-wrap: wrap;
      gap: 0.375rem;
      margin-top: 0.5rem;
    }

    .hashtag {
      padding: 0.25rem 0.625rem;
      font-size: 0.75rem;
      font-weight: 500;
      color: var(--color-brand-600);
      background: var(--color-brand-50);
      border-radius: var(--radius-full);
    }

    :host-context(.dark) .hashtag {
      background: rgba(236, 72, 153, 0.15);
      color: var(--color-brand-400);
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

    /* Mobile responsive (320-767px) */
    @media (max-width: 767px) {
      .modal-content {
        gap: 1rem;
      }

      .image-preview {
        aspect-ratio: 4 / 3;
        max-height: 40vh;
      }

      .image-preview img {
        object-fit: contain;
        background: var(--color-surface-secondary);
      }

      .upload-area {
        aspect-ratio: 4 / 3;
      }

      .upload-area svg {
        width: 32px;
        height: 32px;
      }

      .ai-btn {
        padding: 0.625rem 0.75rem;
        font-size: 0.8125rem;
      }

      .input {
        padding: 0.5rem 0.75rem;
        font-size: 0.8125rem;
      }

      .textarea {
        min-height: 4rem;
      }

      .modal-actions {
        margin: 0 -1rem -1rem -1rem;
        padding: 0.75rem 1rem;
        border-radius: 0;
      }

      .modal-actions .btn {
        flex: 1;
      }
    }
  `]
})
export class PortfolioItemModalComponent implements OnChanges {
  isOpen = input<boolean>(false);
  editItem = input<PortfolioItem | null>(null);
  close = output<void>();
  save = output<{ title: string; description: string; hashtags: string[]; serviceId?: string; imageUrl: string; imageFile?: File }>();

  private authService = inject(AuthService);
  private dataService = inject(DataService);
  private aiService = inject(AIService);
  private notificationService = inject(NotificationService);

  imagePreview = signal<string>('');
  imageBase64 = signal<string>('');
  imageFile = signal<File | null>(null);
  title = '';
  description = '';
  hashtagsInput = '';
  selectedServiceId = '';
  services = signal<BeautyService[]>([]);
  isGenerating = signal(false);

  parsedHashtags = signal<string[]>([]);

  ngOnChanges(): void {
    if (this.isOpen()) {
      this.loadServices();

      const item = this.editItem();
      if (item) {
        this.imagePreview.set(item.imageUrl);
        this.title = item.title;
        this.description = item.description;
        this.hashtagsInput = item.hashtags.join(', ');
        this.selectedServiceId = item.serviceId || '';
        this.updateParsedHashtags();
      } else {
        this.reset();
      }
    }
  }

  private loadServices(): void {
    const masterId = this.authService.masterApiId();
    if (!masterId) return;

    this.dataService.getServices(masterId).subscribe(data => {
      this.services.set(data);
    });
  }

  private reset(): void {
    this.imagePreview.set('');
    this.imageBase64.set('');
    this.imageFile.set(null);
    this.title = '';
    this.description = '';
    this.hashtagsInput = '';
    this.selectedServiceId = '';
    this.parsedHashtags.set([]);
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    this.imageFile.set(file);

    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      this.imagePreview.set(result);
      this.imageBase64.set(result.split(',')[1]);
    };
    reader.readAsDataURL(file);
  }

  removeImage(): void {
    this.imagePreview.set('');
    this.imageBase64.set('');
    this.imageFile.set(null);
  }

  async generateWithAI(): Promise<void> {
    if (!this.imageBase64()) return;

    this.isGenerating.set(true);

    try {
      const result = await this.aiService.generatePortfolioContent(this.imageBase64());

      if (result.description) {
        this.description = result.description;
      }
      if (result.hashtags.length > 0) {
        this.hashtagsInput = result.hashtags.join(', ');
        this.updateParsedHashtags();
      }

      this.notificationService.success('Контент сгенерирован!');
    } catch (error) {
      this.notificationService.error('Ошибка генерации');
    }

    this.isGenerating.set(false);
  }

  updateParsedHashtags(): void {
    const tags = this.hashtagsInput
      .split(',')
      .map(t => t.trim().replace(/^#/, ''))
      .filter(t => t.length > 0);
    this.parsedHashtags.set(tags);
  }

  isValid(): boolean {
    return !!(this.imagePreview() && this.title.trim());
  }

  onSave(): void {
    if (!this.isValid()) return;

    this.updateParsedHashtags();

    this.save.emit({
      title: this.title.trim(),
      description: this.description.trim(),
      hashtags: this.parsedHashtags(),
      serviceId: this.selectedServiceId || undefined,
      imageUrl: this.imagePreview(),
      imageFile: this.imageFile() || undefined
    });
  }
}
