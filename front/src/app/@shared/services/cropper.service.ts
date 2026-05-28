// // src/app/@shared/services/cropper.service.ts
// import { Injectable, ElementRef } from '@angular/core';
// import Cropper from 'cropperjs';


// // use


// //   ngAfterViewInit() {
// //     this.cropperService.initialize(this.modalContent);
// //   }


// //   @ViewChild('fileInput') fileInput!: ElementRef<HTMLInputElement>;
// //   @ViewChild('modalContent') modalContent!: ElementRef<HTMLDivElement>;

// //   isModalVisible: boolean = false;
// //   thumbnailImage: string | null = null;
// //   files: File[] = [];
// //   filekbLoaded: number = 0;
// //   fileLoadedName: string = '';

// //   onSelectImage(): void {
// //     this.fileInput.nativeElement.click();
// //   }

// //   onFileSelected(event: any): void {
// //     const input = event.target;
// //     if (input.files && input.files[0]) {
// //       const file = input.files[0];
// //       this.cropperService.selectImage(file, () => {
// //         this.isModalVisible = true;
// //       });
// //     }
// //   }

// //   async saveEditedMedia(): Promise<void> {
// //     const croppedFile = await this.cropperService.crop();
// //     if (croppedFile) {
// //       this.files.push(croppedFile);
// //       const reader = new FileReader();
// //       reader.onload = () => {
// //         this.thumbnailImage = reader.result as string;
// //       };
// //       reader.readAsDataURL(croppedFile);
// //     }
// //     this.cropperService.cleanup();
// //     this.isModalVisible = false;
// //   }

// //   cancelEditing(): void {
// //     this.cropperService.cleanup();
// //     this.isModalVisible = false;
// //   }

// //   deleteImage(): void {
// //     this.thumbnailImage = null; // تصویر نمایش داده شده پاک بشه
// //     this.files = []; // فایل‌هایی که نگه داشتی پاک بشن
// //     this.filekbLoaded = 0; // مقدار درصد لودینگ پاک بشه
// //     this.fileLoadedName = ''; // نام فایل پاک بشه
// //     if (this.fileInput) {
// //       this.fileInput.nativeElement.value = ''; // ورودی فایل ریست بشه
// //     }
// //   }



// @Injectable({
//   providedIn: 'root',
// })
// export class CropperService {
//   private cropperInstance: Cropper | null = null;
//   private currentFile: File | null = null;
//   private modalContent!: ElementRef<HTMLDivElement>;
//   private asRatio: number = 1 / 1;

//   constructor() {}

//   initialize(modalContentRef: ElementRef<HTMLDivElement>, ratio?: number) {
//     this.modalContent = modalContentRef;
//     if (ratio !== undefined) {
//       this.asRatio = ratio;
//     }
//   }

//   selectImage(file: File, callback: () => void): void {
//     this.currentFile = file;
//     const reader = new FileReader();
//     reader.onload = (e: any) => {
//       this.displayImage(e.target.result);
//       this.initializeCropper(e.target.result);
//       callback(); // مثلا برای باز کردن مدال
//     };
//     reader.readAsDataURL(file);
//   }

//   private displayImage(imageSrc: string): void {
//     const modalContent = this.modalContent?.nativeElement;
//     if (modalContent) {
//       modalContent.innerHTML = '';
//       const img = document.createElement('img');
//       img.src = imageSrc;
//       modalContent.appendChild(img);
//     }
//   }

//   private initializeCropper(imageSrc: string): void {
//     const modalContent = this.modalContent?.nativeElement;
//     if (!modalContent) {
//       console.error('Modal content not found.');
//       return;
//     }
//     const image = modalContent.querySelector('img')!;
//     this.cropperInstance = new Cropper(image, {
//       aspectRatio: this.asRatio,
//       viewMode: 2,
//       movable: true,
//       zoomable: true,
//       scalable: true,
//       autoCropArea: 1,
//       responsive: true,
//       background: true,
//       guides: true,
//       center: true,
//       checkCrossOrigin: false,
//     });
//   }

//   async crop(): Promise<File | null> {
//     if (!this.cropperInstance || !this.currentFile) {
//       return null;
//     }
//     const blob = await this.getCroppedBlob();
//     if (!blob) {
//       return null;
//     }
//     return new File([blob], this.currentFile.name, { type: this.currentFile.type });
//   }

//   private getCroppedBlob(): Promise<Blob | null> {
//     return new Promise((resolve) => {
//       if (!this.cropperInstance) {
//         resolve(null);
//         return;
//       }
//       this.cropperInstance.getCroppedCanvas().toBlob((blob) => {
//         resolve(blob);
//       });
//     });
//   }

//   cleanup(): void {
//     if (this.cropperInstance) {
//       this.cropperInstance.destroy();
//       this.cropperInstance = null;
//     }
//     this.currentFile = null;
//     if (this.modalContent?.nativeElement) {
//       this.modalContent.nativeElement.innerHTML = '';
//     }
//   }
// }
