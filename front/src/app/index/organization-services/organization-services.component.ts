import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTabsModule } from '@angular/material/tabs';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatMenuModule } from '@angular/material/menu';
import { MatSelectModule } from '@angular/material/select';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDividerModule } from '@angular/material/divider';
import { MatChipsModule } from '@angular/material/chips';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { IndexHttpService } from '../index-http.service';
import { ToastService } from '../../@shared/services/toast/toast.service';
import { ThemeService } from '../../@shared/services/theme.service';
import { TranslationService } from '../../@shared/services/translation.service';
import { finalize } from 'rxjs/operators';
import { Observable } from 'rxjs';

@Component({
  selector: 'app-organization-services',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatTabsModule,
    MatExpansionModule,
    MatMenuModule,
    MatSelectModule,
    MatTooltipModule,
    MatDividerModule,
    MatChipsModule,
    RouterModule,
  ],
  templateUrl: './organization-services.component.html',
  styleUrls: ['./organization-services.component.scss'],
})
export class OrganizationServicesComponent implements OnInit {
  organizationId: string | null = null;
  organization: any = null;
  services: any[] = [];
  staffList: any[] = [];
  resources: any[] = [];
  isLoading = false;
  isOrgLoading = false;
  isLoadingStaff = false;
  isLoadingResources = false;

  currentLang$: Observable<string>;
  isDarkMode$: Observable<boolean>;

  constructor(
    private route: ActivatedRoute,
    private indexHttpService: IndexHttpService,
    private toastService: ToastService,
    private cdr: ChangeDetectorRef,
    private router: Router,
    public themeService: ThemeService,
    public translationService: TranslationService
  ) {
    this.currentLang$ = this.translationService.currentLang$;
    this.isDarkMode$ = this.themeService.isDarkMode$;
  }



  ngOnInit(): void {
      // this.fetchOrganizationDetails();
      this.fetchOrganizationServices();
      this.fetchStaffList();
      this.fetchResourceList();
  }

  toggleTheme(): void {
    this.themeService.toggleTheme();
  }

  changeLanguage(lang: string): void {
    this.translationService.setLanguage(lang);
  }

  getTranslate(key: string): string {
    return this.translationService.getTranslation(key);
  }



  fetchOrganizationServices(): void {
    this.isLoading = true;
    const payload = {
      is_paginate: true,
      count_item: 10,
    };

    this.indexHttpService
      .getOrganizationServices(payload)
      .pipe(
        finalize(() => {
          this.isLoading = false;
          this.cdr.detectChanges();
        })
      )
      .subscribe({
        next: (res) => {
          if (res && res.success) {
            if (Array.isArray(res.data)) {
              this.services = res.data;
            } else if (res.data && res.data.data) {
              this.services = res.data.data;
            }
          }
        },
        error: (err) => {
          console.error('Error fetching services:', err);
          this.toastService.error('خطا در دریافت لیست خدمات');
        },
      });
  }

  fetchStaffList(): void {
    this.isLoadingStaff = true;
    const payload = {
      is_paginate: true,
      count_item: 10,
    };

    this.indexHttpService
      .getStaffList(payload)
      .pipe(
        finalize(() => {
          this.isLoadingStaff = false;
          this.cdr.detectChanges();
        })
      )
      .subscribe({
        next: (res) => {
          if (res && res.success) {
            if (Array.isArray(res.data)) {
              this.staffList = res.data;
            } else if (res.data && res.data.data) {
              this.staffList = res.data.data;
            }
          }
        },
        error: (err) => {
          console.error('Error fetching staff list:', err);
        },
      });
  }

  fetchResourceList(): void {
    this.isLoadingResources = true;
    const payload = {
      is_paginate: true,
      count_item: 10,
    };

    this.indexHttpService
      .getResourceList(payload)
      .pipe(
        finalize(() => {
          this.isLoadingResources = false;
          this.cdr.detectChanges();
        })
      )
      .subscribe({
        next: (res) => {
          if (res && res.success) {
            if (Array.isArray(res.data)) {
              this.resources = res.data;
            } else if (res.data && res.data.data) {
              this.resources = res.data.data;
            }
          }
        },
        error: (err) => {
          console.error('Error fetching resource list:', err);
        },
      });
  }

  goToStaffDetails(staffId: any): void {
    this.router.navigate(['/staff-details', staffId]);
  }

  goToAppointment(serviceId: any): void {
    this.router.navigate(['/appointment'], {
      queryParams: { 
        service_id: serviceId,
        mode: 'user'
      },
    });
  }

  goToStaffAppointment(staffId: any): void {
    this.router.navigate(['/appointment'], {
      queryParams: { 
        staff_id: staffId,
        mode: 'user'
      },
    });
  }

  getPlaceholderColor(name: string): string {
    const colors = [
      'linear-gradient(135deg, #6366f1 0%, #a855f7 100%)',
      'linear-gradient(135deg, #3b82f6 0%, #2dd4bf 100%)',
      'linear-gradient(135deg, #f59e0b 0%, #ef4444 100%)',
      'linear-gradient(135deg, #10b981 0%, #3b82f6 100%)',
      'linear-gradient(135deg, #ec4899 0%, #8b5cf6 100%)',
      'linear-gradient(135deg, #f97316 0%, #eab308 100%)',
    ];
    if (!name) return colors[0];
    let hash = 0;
    for (let i = 0; i < name.length; i++) {
      hash = name.charCodeAt(i) + ((hash << 5) - hash);
    }
    return colors[Math.abs(hash) % colors.length];
  }
}
