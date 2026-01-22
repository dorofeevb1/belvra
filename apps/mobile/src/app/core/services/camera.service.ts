import { Injectable } from '@angular/core';
import { Capacitor } from '@capacitor/core';
import {
  Camera,
  CameraResultType,
  CameraSource,
  Photo,
  ImageOptions
} from '@capacitor/camera';

export interface CameraPhoto {
  dataUrl?: string;
  webPath?: string;
  blob?: Blob;
  format: string;
}

@Injectable({
  providedIn: 'root'
})
export class CameraService {
  private readonly isNative = Capacitor.isNativePlatform();

  async takePicture(options?: Partial<ImageOptions>): Promise<CameraPhoto | null> {
    try {
      const photo = await Camera.getPhoto({
        quality: 90,
        allowEditing: true,
        resultType: CameraResultType.DataUrl,
        source: CameraSource.Camera,
        ...options
      });

      return this.processPhoto(photo);
    } catch (error) {
      console.error('Camera error:', error);
      return null;
    }
  }

  async selectFromGallery(options?: Partial<ImageOptions>): Promise<CameraPhoto | null> {
    try {
      const photo = await Camera.getPhoto({
        quality: 90,
        allowEditing: true,
        resultType: CameraResultType.DataUrl,
        source: CameraSource.Photos,
        ...options
      });

      return this.processPhoto(photo);
    } catch (error) {
      console.error('Gallery selection error:', error);
      return null;
    }
  }

  async selectMultipleFromGallery(limit: number = 10): Promise<CameraPhoto[]> {
    try {
      const result = await Camera.pickImages({
        quality: 90,
        limit
      });

      const photos: CameraPhoto[] = [];
      for (const photo of result.photos) {
        const processed = await this.processGalleryPhoto(photo);
        if (processed) {
          photos.push(processed);
        }
      }

      return photos;
    } catch (error) {
      console.error('Multiple selection error:', error);
      return [];
    }
  }

  async promptForSource(): Promise<CameraPhoto | null> {
    try {
      const photo = await Camera.getPhoto({
        quality: 90,
        allowEditing: true,
        resultType: CameraResultType.DataUrl,
        source: CameraSource.Prompt, // Shows action sheet to choose camera or gallery
        promptLabelHeader: 'Выберите источник',
        promptLabelPhoto: 'Галерея',
        promptLabelPicture: 'Камера'
      });

      return this.processPhoto(photo);
    } catch (error) {
      console.error('Photo selection error:', error);
      return null;
    }
  }

  private processPhoto(photo: Photo): CameraPhoto {
    return {
      dataUrl: photo.dataUrl,
      webPath: photo.webPath,
      format: photo.format
    };
  }

  private async processGalleryPhoto(photo: { webPath?: string; format: string }): Promise<CameraPhoto | null> {
    if (!photo.webPath) return null;

    // For gallery photos, we need to fetch the blob
    try {
      const response = await fetch(photo.webPath);
      const blob = await response.blob();

      return {
        webPath: photo.webPath,
        blob,
        format: photo.format
      };
    } catch {
      return {
        webPath: photo.webPath,
        format: photo.format
      };
    }
  }

  // Convert dataUrl to Blob for upload
  dataUrlToBlob(dataUrl: string): Blob {
    const arr = dataUrl.split(',');
    const mime = arr[0].match(/:(.*?);/)?.[1] || 'image/jpeg';
    const bstr = atob(arr[1]);
    let n = bstr.length;
    const u8arr = new Uint8Array(n);

    while (n--) {
      u8arr[n] = bstr.charCodeAt(n);
    }

    return new Blob([u8arr], { type: mime });
  }

  // Convert photo to File for FormData upload
  photoToFile(photo: CameraPhoto, filename: string = 'photo.jpg'): File | null {
    if (photo.blob) {
      return new File([photo.blob], filename, { type: `image/${photo.format}` });
    }

    if (photo.dataUrl) {
      const blob = this.dataUrlToBlob(photo.dataUrl);
      return new File([blob], filename, { type: `image/${photo.format}` });
    }

    return null;
  }
}
