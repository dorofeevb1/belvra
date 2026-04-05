import { UserSubscription } from './subscription.model';

export type UserRole = 'master' | 'client';

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  phone?: string;
  avatar?: string;
  hasMasterProfile?: boolean;
  isVerified?: boolean;
  isEarlyAdopter?: boolean;
  createdAt: Date;
}

export interface SocialLinks {
  telegram?: string;
  instagram?: string;
  vk?: string;
  whatsapp?: string;
}

export interface NotificationSettings {
  emailNotifications: boolean;
  smsNotifications: boolean;
  pushNotifications: boolean;
  reminderHours: number; // Hours before appointment to send reminder
}

export interface Master extends User {
  role: 'master';
  masterProfileId?: string; // ID of master profile (different from user id)
  specialization: string;
  description?: string;
  address: string;
  coordinates?: {
    lat: number;
    lng: number;
  };
  experienceYears?: number;
  isAvailable?: boolean;
  rating: number;
  reviewsCount: number;
  workSchedule: WorkSchedule;
  services: string[];
  socialLinks?: SocialLinks;
  notificationSettings?: NotificationSettings;
  subscription?: UserSubscription;
  isPro?: boolean;
  distanceKm?: number | null;
}

export interface Client extends User {
  role: 'client';
  favoritesMasters?: string[];
  notificationSettings?: NotificationSettings;
  subscription?: UserSubscription;
}

export interface WorkSchedule {
  monday: DaySchedule | null;
  tuesday: DaySchedule | null;
  wednesday: DaySchedule | null;
  thursday: DaySchedule | null;
  friday: DaySchedule | null;
  saturday: DaySchedule | null;
  sunday: DaySchedule | null;
}

export interface DaySchedule {
  start: string;
  end: string;
}

export interface AuthCredentials {
  email: string;
  password: string;
  role: UserRole;
}
