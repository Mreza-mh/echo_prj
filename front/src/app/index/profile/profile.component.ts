import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { AuthHTTPService } from '../../auth/auth-http.service';
import { ToastService } from '../../@shared/services/toast/toast.service';
import { TranslationService } from '../../@shared/services/translation.service';
import { finalize } from 'rxjs/operators';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule
  ],
  templateUrl: './profile.component.html',
  styleUrls: ['./profile.component.scss']
})
export class ProfileComponent implements OnInit {
  profileForm: FormGroup;
  isLoading = false;
  isSaving = false;
  userData: any = {};

  constructor(
    private fb: FormBuilder,
    private authHttpService: AuthHTTPService,
    private toastService: ToastService,
    private cdr: ChangeDetectorRef,
    private translationService: TranslationService
  ) {
    this.profileForm = this.fb.group({
      name: ['', Validators.required],
      birthday: [''],
    });
  }

  ngOnInit(): void {
    this.loadProfile();
  }

  getDirection(): 'ltr' | 'rtl' {
    return this.translationService.getDirection();
  }

  loadProfile(): void {
    if (this.isLoading) return;
    this.isLoading = true;
    this.cdr.detectChanges();

    this.authHttpService.getMe().subscribe({
      next: (response) => {
        console.log('Profile data received:', response);
        if (response.success && response.data) {
          this.userData = response.data;
          this.profileForm.patchValue({
            name: this.userData.name,
            birthday: this.userData.birthday,
          });
        }
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: (error) => {
        console.error('Error loading profile:', error);
        this.toastService.error('خطا در دریافت اطلاعات پروفایل');
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      complete: () => {
        this.isLoading = false;
        this.cdr.detectChanges();
      }
    });
  }

  formatDate(dateStr: string): string {
    if (!dateStr) return '—';
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('fa-IR', { year: 'numeric', month: 'long' });
    } catch {
      return dateStr.slice(0, 10);
    }
  }

  getUserRoleLabel(role: string): string {
    switch (role) {
      case 'super_admin': return 'مدیر ارشد';
      case 'admin': return 'مدیر سیستم';
      case 'user': return 'کاربر عادی';
      default: return role || 'نامشخص';
    }
  }

  onSubmit(): void {
    if (this.profileForm.valid && !this.isSaving) {
      this.isSaving = true;
      this.cdr.detectChanges();
      
      const formData = {
        name: this.profileForm.value.name,
        birthday: this.profileForm.value.birthday
      };

      this.authHttpService.editProfile(formData).subscribe({
        next: (response) => {
          if (response.success) {
            this.toastService.success('پروفایل با موفقیت بروزرسانی شد');
          } else {
            this.toastService.error(response.message || 'خطا در بروزرسانی پروفایل');
          }
          this.isSaving = false;
          this.cdr.detectChanges();
        },
        error: (error) => {
          this.toastService.error('خطا در برقراری ارتباط با سرور');
          this.isSaving = false;
          this.cdr.detectChanges();
        },
        complete: () => {
          this.isSaving = false;
          this.cdr.detectChanges();
        }
      });
    }
  }
}
