import { Injectable } from '@angular/core';
import { Capacitor } from '@capacitor/core';
import { Preferences } from '@capacitor/preferences';

@Injectable({
  providedIn: 'root'
})
export class StorageService {
  private readonly isNative = Capacitor.isNativePlatform();

  async get(key: string): Promise<string | null> {
    if (this.isNative) {
      const result = await Preferences.get({ key });
      return result.value;
    }
    return localStorage.getItem(key);
  }

  async set(key: string, value: string): Promise<void> {
    if (this.isNative) {
      await Preferences.set({ key, value });
    } else {
      localStorage.setItem(key, value);
    }
  }

  async remove(key: string): Promise<void> {
    if (this.isNative) {
      await Preferences.remove({ key });
    } else {
      localStorage.removeItem(key);
    }
  }

  async clear(): Promise<void> {
    if (this.isNative) {
      await Preferences.clear();
    } else {
      localStorage.clear();
    }
  }

  async keys(): Promise<string[]> {
    if (this.isNative) {
      const result = await Preferences.keys();
      return result.keys;
    }
    return Object.keys(localStorage);
  }

  // Convenience methods for JSON data
  async getObject<T>(key: string): Promise<T | null> {
    const value = await this.get(key);
    if (value) {
      try {
        return JSON.parse(value) as T;
      } catch {
        return null;
      }
    }
    return null;
  }

  async setObject<T>(key: string, value: T): Promise<void> {
    await this.set(key, JSON.stringify(value));
  }
}
