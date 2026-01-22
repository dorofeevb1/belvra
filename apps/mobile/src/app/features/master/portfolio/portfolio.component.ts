import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuthService, DataService, NotificationService } from '../../../core/services';
import { SubscriptionService } from '../../../core/services/subscription.service';
import { PortfolioItem } from '../../../core/models';
import { DateFormatPipe } from '../../../shared/pipes/date-format.pipe';
import { PortfolioItemModalComponent } from './portfolio-item-modal.component';

@Component({
  selector: 'app-portfolio',
  standalone: true,
  imports: [
    CommonModule,
    DateFormatPipe,
    PortfolioItemModalComponent
  ],
  templateUrl: './portfolio.component.html',
  styleUrl: './portfolio.component.scss'
})
export class PortfolioComponent implements OnInit {
  private authService = inject(AuthService);
  private dataService = inject(DataService);
  private notificationService = inject(NotificationService);
  private subscriptionService = inject(SubscriptionService);

  isLoading = signal(true);
  portfolio = signal<PortfolioItem[]>([]);
  showModal = signal(false);
  editingItem = signal<PortfolioItem | null>(null);

  ngOnInit(): void {
    this.loadData();
  }

  private loadData(): void {
    const masterId = this.authService.masterApiId();
    if (!masterId) return;

    this.dataService.getPortfolio(masterId).subscribe(data => {
      this.portfolio.set(data);
      this.isLoading.set(false);
    });
  }

  openAddModal(): void {
    if (!this.subscriptionService.canAddPortfolioItem()) {
      this.notificationService.warning('Достигнут лимит портфолио. Перейдите на PRO для добавления неограниченного количества работ.');
      return;
    }
    this.editingItem.set(null);
    this.showModal.set(true);
  }

  openEditModal(item: PortfolioItem): void {
    this.editingItem.set(item);
    this.showModal.set(true);
  }

  closeModal(): void {
    this.showModal.set(false);
    this.editingItem.set(null);
  }

  onSave(data: { title: string; description: string; hashtags: string[]; serviceId?: string; imageUrl: string; imageFile?: File }): void {
    const masterId = this.authService.masterApiId();
    if (!masterId) return;

    if (this.editingItem()) {
      this.dataService.updatePortfolioItem(this.editingItem()!.id, data, data.imageFile).subscribe(updated => {
        this.portfolio.update(list =>
          list.map(item => item.id === updated.id ? updated : item)
        );
        this.notificationService.success('Работа обновлена');
        this.closeModal();
      });
    } else {
      this.dataService.addPortfolioItem({
        masterId,
        ...data
      }, data.imageFile).subscribe(newItem => {
        this.portfolio.update(list => [newItem, ...list]);
        this.notificationService.success('Работа добавлена');
        this.closeModal();
      });
    }
  }

  deleteItem(id: string): void {
    if (!confirm('Удалить эту работу?')) return;

    this.dataService.deletePortfolioItem(id).subscribe(() => {
      this.portfolio.update(list => list.filter(item => item.id !== id));
      this.notificationService.success('Работа удалена');
    });
  }
}
