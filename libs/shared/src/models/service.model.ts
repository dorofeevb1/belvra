export interface BeautyService {
  id: string;
  masterId: string;
  serviceId?: string; // Global catalog service ID (for creating MasterService)
  name: string;
  description?: string;
  duration: number;
  price: number;
  defaultMaterialsCost: number;
  category: ServiceCategory;
  isActive: boolean;
}

export type ServiceCategory =
  | 'manicure'
  | 'pedicure'
  | 'hair'
  | 'makeup'
  | 'eyebrows'
  | 'lashes'
  | 'cosmetology'
  | 'massage'
  | 'other';

export const SERVICE_CATEGORIES: { value: ServiceCategory; label: string }[] = [
  { value: 'manicure', label: 'Маникюр' },
  { value: 'pedicure', label: 'Педикюр' },
  { value: 'hair', label: 'Волосы' },
  { value: 'makeup', label: 'Макияж' },
  { value: 'eyebrows', label: 'Брови' },
  { value: 'lashes', label: 'Ресницы' },
  { value: 'cosmetology', label: 'Косметология' },
  { value: 'massage', label: 'Массаж' },
  { value: 'other', label: 'Другое' }
];

export interface Material {
  id: string;
  name: string;
  unit: string;
  pricePerUnit: number;
}

export interface UsedMaterial {
  materialId: string;
  name: string;
  quantity: number;
  totalCost: number;
}
