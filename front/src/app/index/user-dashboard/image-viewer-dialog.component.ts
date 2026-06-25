import { Component, Inject, inject, HostListener } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { CommonModule } from '@angular/common';
import { MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslationService } from '../../@shared/services/translation.service';

export interface ImageViewerData {
  imageUrl?: string;
  images?: string[];
  currentIndex?: number;
}

@Component({
  selector: 'app-image-viewer-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatButtonModule,
    MatIcon,
    MatTooltipModule
  ],
  templateUrl: './image-viewer-dialog.component.html',
  styleUrls: ['./image-viewer-dialog.component.scss']
})
export class ImageViewerDialogComponent {
  private translationService = inject(TranslationService);

  images: string[] = [];
  currentIndex = 0;

  getTranslation(key: string): string {
    return this.translationService.getTranslation(key);
  }

  constructor(
    public dialogRef: MatDialogRef<ImageViewerDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: ImageViewerData
  ) {
    if (data.images && data.images.length > 0) {
      this.images = data.images;
      this.currentIndex = data.currentIndex ?? 0;
    } else if (data.imageUrl) {
      this.images = [data.imageUrl];
      this.currentIndex = 0;
    }
  }

  get currentImage(): string {
    return this.images[this.currentIndex] ?? '';
  }

  get hasMultiple(): boolean {
    return this.images.length > 1;
  }

  prev(): void {
    if (this.currentIndex > 0) this.currentIndex--;
  }

  next(): void {
    if (this.currentIndex < this.images.length - 1) this.currentIndex++;
  }

  goTo(index: number): void {
    this.currentIndex = index;
  }

  @HostListener('document:keydown', ['$event'])
  onKey(e: KeyboardEvent): void {
    if (e.key === 'ArrowLeft') this.next();
    if (e.key === 'ArrowRight') this.prev();
    if (e.key === 'Escape') this.dialogRef.close();
  }

  onClose(): void {
    this.dialogRef.close();
  }
}
