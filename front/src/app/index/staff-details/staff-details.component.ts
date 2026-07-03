import { Component, OnInit, ChangeDetectorRef, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { IndexHttpService } from '../index-http.service';
import { ToastService } from '../../@shared/services/toast/toast.service';
import { TranslationService } from '../../@shared/services/translation.service';
import { finalize } from 'rxjs/operators';

@Component({
  selector: 'app-staff-details',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    RouterModule
  ],
  templateUrl: './staff-details.component.html',
  styleUrls: ['./staff-details.component.scss']
})
export class StaffDetailsComponent implements OnInit {
  private translationService = inject(TranslationService);

  getTranslation(key: string): string {
    return this.translationService.getTranslation(key);
  }

  staffId: string | null = null;
  staff: any = null;
  isLoading = false;

  readonly weekDays: { key: string; labelKey: string }[] = [
    { key: 'saturday', labelKey: 'sat' },
    { key: 'sunday', labelKey: 'sun' },
    { key: 'monday', labelKey: 'mon' },
    { key: 'tuesday', labelKey: 'tue' },
    { key: 'wednesday', labelKey: 'wed' },
    { key: 'thursday', labelKey: 'thu' },
    { key: 'friday', labelKey: 'fri' },
  ];

  // getDay(): 0=Sunday ... 6=Saturday
  private readonly jsDayToKey = [
    'sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'
  ];
  readonly todayKey = this.jsDayToKey[new Date().getDay()];

  getDaySlots(dayKey: string): { start: string; end: string }[] {
    const day = (this.staff?.schedule || []).find((s: any) => s.day === dayKey);
    return day?.slots || [];
  }

  get workingDaysCount(): number {
    return (this.staff?.schedule || []).filter((d: any) => d.slots?.length).length;
  }

  constructor(
    private route: ActivatedRoute,
    private indexHttpService: IndexHttpService,
    private toastService: ToastService,
    private cdr: ChangeDetectorRef,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.staffId = this.route.snapshot.paramMap.get('id');
    if (this.staffId) {
      this.fetchStaffDetails();
    } else {
      this.toastService.error('شناسه کارمند یافت نشد');
      this.router.navigate(['/organizations']);
    }
  }

  fetchStaffDetails(): void {
    this.isLoading = true;
    this.indexHttpService.getStaffDetails(this.staffId!)
      .pipe(finalize(() => {
        this.isLoading = false;
        this.cdr.detectChanges();
      }))
      .subscribe({
        next: (res) => {
          if (res && res.success) {
            this.staff = res.data;
          } else {
            this.toastService.error('خطا در دریافت اطلاعات کارمند');
          }
        },
        error: (err) => {
          console.error('Error fetching staff details:', err);
          this.toastService.error('خطا در ارتباط با سرور');
        }
      });
  }

  goToAppointment(): void {
    if (this.staff ) {
      this.router.navigate(['/appointment'], {
        queryParams: {
          staff_id: this.staffId,
          mode: 'user'
        }
      });
    }
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
