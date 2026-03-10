import { describe, it, expect, vi } from 'vitest';

/**
 * DataService tests — we test the pure mapper/helper methods without Angular DI.
 * We extract the private methods by creating a minimal instance and calling them
 * via `(service as any).methodName(...)`.
 */

// Stub localStorage (some transitive code might reference it)
const store: Record<string, string> = {};
if (typeof globalThis.localStorage === 'undefined') {
  Object.defineProperty(globalThis, 'localStorage', {
    value: {
      getItem: (k: string) => store[k] ?? null,
      setItem: (k: string, v: string) => { store[k] = v; },
      removeItem: (k: string) => { delete store[k]; },
      clear: () => { for (const k of Object.keys(store)) delete store[k]; },
    },
    writable: true,
  });
}

import { DataService } from './data.service';

/**
 * Create a minimal DataService without Angular DI.
 */
function createService(): DataService {
  const svc = Object.create(DataService.prototype) as DataService;

  // Mock injected deps
  Object.defineProperty(svc, 'api', { value: {}, writable: true });
  Object.defineProperty(svc, 'auth', { value: {}, writable: true });
  Object.defineProperty(svc, 'DELAY', { value: 300, writable: true });
  Object.defineProperty(svc, 'MEDIA_BASE_URL', { value: 'http://localhost:8000', writable: true });

  return svc;
}

describe('DataService', () => {
  const service = createService();

  // ---------- getFullMediaUrl ----------

  describe('getFullMediaUrl', () => {
    const getFullMediaUrl = (url: string | null) => (service as any).getFullMediaUrl(url);

    it('returns empty string for null', () => {
      expect(getFullMediaUrl(null)).toBe('');
    });

    it('returns empty string for empty string', () => {
      expect(getFullMediaUrl('')).toBe('');
    });

    it('returns the URL as-is when it starts with http', () => {
      const url = 'https://cdn.example.com/photo.jpg';
      expect(getFullMediaUrl(url)).toBe(url);
    });

    it('returns the URL as-is for http (not https)', () => {
      const url = 'http://example.com/img.png';
      expect(getFullMediaUrl(url)).toBe(url);
    });

    it('prepends MEDIA_BASE_URL for relative paths', () => {
      expect(getFullMediaUrl('/media/photos/1.jpg')).toBe('http://localhost:8000/media/photos/1.jpg');
    });
  });

  // ---------- mapBackendAppointment ----------

  describe('mapBackendAppointment', () => {
    const mapApt = (data: any) => (service as any).mapBackendAppointment(data);

    it('maps all backend fields correctly', () => {
      const backend = {
        id: 'apt-1',
        master: { id: 'm1' },
        client: { id: 'c1', full_name: 'Ivan Ivanov', phone: '+71234567890' },
        service: { id: 's1', name: 'Haircut', duration: 45 },
        date: '2026-03-15',
        start_time: '10:00:00',
        end_time: '10:45:00',
        price: '1500.00',
        status: 'confirmed',
        notes: 'no notes',
        created_at: '2026-03-10T10:00:00Z',
        updated_at: '2026-03-10T12:00:00Z',
        prepaid: 500,
        payment_status: 'paid',
      };

      const result = mapApt(backend);

      expect(result.id).toBe('apt-1');
      expect(result.masterId).toBe('m1');
      expect(result.clientId).toBe('c1');
      expect(result.serviceId).toBe('s1');
      expect(result.serviceName).toBe('Haircut');
      expect(result.clientName).toBe('Ivan Ivanov');
      expect(result.clientPhone).toBe('+71234567890');
      expect(result.date).toBe('2026-03-15');
      expect(result.startTime).toBe('10:00');
      expect(result.endTime).toBe('10:45');
      expect(result.duration).toBe(45);
      expect(result.price).toBe(1500);
      expect(result.status).toBe('confirmed');
      expect(result.notes).toBe('no notes');
      expect(result.prepaid).toBe(500);
      expect(result.paymentStatus).toBe('paid');
    });

    it('handles scalar master/client/service IDs (not objects)', () => {
      const backend = {
        id: 'apt-2',
        master: 'm2',
        client: 'c2',
        service: 's2',
        service_name: 'Manicure',
        client_name: 'Client Name',
        date: '2026-03-16',
        start_time: '14:00',
        end_time: '15:00',
        price: '2000',
        status: 'pending',
        created_at: '2026-03-10T10:00:00Z',
      };

      const result = mapApt(backend);
      expect(result.masterId).toBe('m2');
      expect(result.clientId).toBe('c2');
      expect(result.serviceId).toBe('s2');
      expect(result.serviceName).toBe('Manicure');
      expect(result.clientName).toBe('Client Name');
    });

    it('maps unknown status to pending', () => {
      const backend = {
        id: 'apt-3',
        master: 'm1',
        client: 'c1',
        service: 's1',
        date: '2026-03-17',
        start_time: '09:00',
        end_time: '10:00',
        price: '500',
        status: 'some_unknown_status',
        created_at: '2026-03-10T10:00:00Z',
      };

      expect(mapApt(backend).status).toBe('pending');
    });
  });

  // ---------- mapBackendReview ----------

  describe('mapBackendReview', () => {
    const mapReview = (data: any) => (service as any).mapBackendReview(data);

    it('handles appointment as UUID string (appointmentId fallback)', () => {
      const backend = {
        id: 'rev-1',
        appointment: 'apt-uuid-123',
        rating: 5,
        comment: 'Great!',
        created_at: '2026-03-10T10:00:00Z',
      };

      const result = mapReview(backend);
      // When appointment is a string, appointmentId falls back to the string itself
      expect(result.appointmentId).toBe('apt-uuid-123');
      // masterId comes from appointment?.master which is undefined for a string
      expect(result.masterId).toBe('');
      expect(result.rating).toBe(5);
      expect(result.comment).toBe('Great!');
    });

    it('handles appointment as object — extracts master, client, id', () => {
      const backend = {
        id: 'rev-2',
        appointment: {
          id: 'apt-obj-456',
          master: 'master-2',
          client: 'client-2',
          client_name: 'Maria',
        },
        rating: 4,
        comment: 'Good',
        created_at: '2026-03-10T10:00:00Z',
      };

      const result = mapReview(backend);
      expect(result.appointmentId).toBe('apt-obj-456');
      expect(result.masterId).toBe('master-2');
      expect(result.clientId).toBe('client-2');
      expect(result.clientName).toBe('Maria');
    });

    it('defaults clientName to "Клиент" when appointment has no client_name', () => {
      const backend = {
        id: 'rev-3',
        appointment: { id: 'apt-1', master: 'm1', client: 'c1' },
        rating: 5,
        created_at: '2026-03-10T10:00:00Z',
      };

      expect(mapReview(backend).clientName).toBe('Клиент');
    });

    it('defaults comment to empty string when not provided', () => {
      const backend = {
        id: 'rev-4',
        appointment: 'apt-1',
        rating: 3,
        created_at: '2026-03-10T10:00:00Z',
      };

      expect(mapReview(backend).comment).toBe('');
    });
  });
});
