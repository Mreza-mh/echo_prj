import { Component, OnInit, OnDestroy, inject, ViewChild, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDividerModule } from '@angular/material/divider';
import { DoctorHttpService } from '../doctor-http.service';
import { ToastService } from '../../@shared/services/toast/toast.service';
import { TranslationService } from '../../@shared/services/translation.service';
import { format } from 'date-fns';

// FullCalendar Imports
import { FullCalendarModule, FullCalendarComponent } from '@fullcalendar/angular';
import { CalendarOptions, EventInput } from '@fullcalendar/core';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import listPlugin from '@fullcalendar/list';
import interactionPlugin from '@fullcalendar/interaction';
import resourceTimelinePlugin from '@fullcalendar/resource-timeline';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-doctor-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatDatepickerModule,
    MatNativeDateModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    MatIconModule,
    MatButtonModule,
    MatCardModule,
    MatDividerModule,
    FullCalendarModule,
    RouterLink
  ],
  templateUrl: './doctor-dashboard.component.html',
  styleUrls: ['./doctor-dashboard.component.scss'],
})
export class DoctorDashboardComponent implements OnInit, OnDestroy {
  @ViewChild('calendar') calendarComponent!: FullCalendarComponent;

  private doctorHttp = inject(DoctorHttpService);
  private toast = inject(ToastService);
  private translationService = inject(TranslationService);
  private cdr = inject(ChangeDetectorRef);

  selectedDate: Date = new Date();
  dashboardData: any = null;
  allAppointments: any[] = [];
  isLoading = false;

  private viewStart: Date = new Date();
  private viewEnd: Date = new Date();

  calendarTitle = '';
  currentViewType = 'resourceTimelineDay';

  // Doctor-specific data
  currentAppointment: any = null;
  currentPatientDetails: any = null;
  staffId: number | null = null;

  // FullCalendar Options
  calendarOptions: CalendarOptions = {
    plugins: [resourceTimelinePlugin, interactionPlugin, dayGridPlugin, timeGridPlugin, listPlugin],
    initialView: 'resourceTimelineDay',
    headerToolbar: false,
    datesSet: (info) => {
      // پایان بازه FullCalendar exclusive است — ۱ میلی‌ثانیه کم می‌کنیم تا آخرین روز واقعی به دست بیاید
      const inclusiveEnd = new Date(info.end.getTime() - 1);

      const sameRange =
        this.viewStart.getTime() === info.start.getTime() &&
        this.viewEnd.getTime() === inclusiveEnd.getTime() &&
        this.currentViewType === info.view.type;

      this.currentViewType = info.view.type;
      this.calendarTitle   = info.view.title;
      this.cdr.detectChanges();

      if (sameRange) return;

      this.viewStart    = info.start;
      this.viewEnd      = inclusiveEnd;
      this.selectedDate = info.start;
      this.loadData();
    },
    resourceAreaHeaderContent: 'پرسنل و منابع',
    resourceAreaWidth: '200px',
    slotMinTime: '07:00:00',
    slotMaxTime: '23:00:00',
    locale: 'fa',
    direction: 'rtl',
    firstDay: 6,
    height: '650px',
    nowIndicator: true,
    editable: false,
    selectable: false,
    eventConstraint: { startTime: '00:00', endTime: '24:00' },
    selectConstraint: { startTime: '00:00', endTime: '24:00' },
    eventDidMount: (info) => {
      const status = info.event.extendedProps['status_title'];
      if (status && info.event.display !== 'background') {
        info.el.classList.add(`event-status-${status}`);
      }
    },
    resourceLabelDidMount: (info) => {
      const expertise = info.resource.extendedProps['expertise'];
      const mainCell = info.el.querySelector('.fc-datagrid-cell-main') as HTMLElement;
      if (mainCell && expertise) {
        const subTitle = document.createElement('div');
        subTitle.className = 'resource-expertise-sub';
        subTitle.innerText = expertise;
        mainCell.appendChild(subTitle);
      }
    },
  };

  ngOnInit(): void {
    this.isLoading = true;
    this.doctorHttp.getCurrentUser().subscribe({
      next: (res: any) => {
        // getMe() اکنون رابطه staffs کاربر را هم برمی‌گرداند — شناسه‌ی واقعی Staff (نه User) لازم است
        const staff = res.data?.staffs?.[0];
        if (res.success && staff) {
          this.staffId = staff.id;
          this.loadData();
        } else {
          this.isLoading = false;
          this.toast.error('این کاربر به‌عنوان پرسنل ثبت نشده است');
        }
      },
      error: (err) => {
        console.error('Error fetching current user:', err);
        this.isLoading = false;
        this.toast.error('خطا در دریافت اطلاعات کاربر');
      },
    });
  }

  loadData(): void {
    if (this.staffId === null) return;
    this.isLoading = true;
    const startStr = format(this.viewStart, 'yyyy-MM-dd');
    const endStr   = format(this.viewEnd,   'yyyy-MM-dd');

    this.doctorHttp
      .getCalendarDashboard({ start_date: startStr, end_date: endStr, staff_ids: [this.staffId] })
      .subscribe({
        next: (res: any) => {
          if (res.success && res.data) {
            this.dashboardData = res.data;
            this.isLoading = false;
            this.cdr.detectChanges();
            this.updateCalendarData();
            this.loadDoctorSpecificData();
          }
        },
        error: (err) => {
          console.error('Error fetching calendar dashboard:', err);
          this.isLoading = false;
          this.toast.error('خطا در بارگذاری اطلاعات تقویم');
        },
      });
  }

  private updateCalendarData(): void {
    if (!this.dashboardData) return;

    setTimeout(() => {
      const resources = this.dashboardData.timeline.map((staff: any) => ({
        id: String(staff.staff_id),
        title: staff.staff_name,
        extendedProps: { expertise: staff.expertise, working_hours: staff.working_hours },
      }));

      const events: EventInput[] = [];
      this.allAppointments = [];
      let minHour = 24,
        maxHour = 0;

      this.dashboardData.timeline.forEach((staff: any) => {
        if (staff.working_hours) {
          const startH = parseInt(staff.working_hours.start.split(':')[0]);
          const endH = parseInt(staff.working_hours.end.split(':')[0]);
          if (startH < minHour) minHour = startH;
          if (endH > maxHour) maxHour = endH;

          events.push({
            resourceId: String(staff.staff_id),
            start: `${this.dashboardData.date}T${staff.working_hours.start}:00`,
            end: `${this.dashboardData.date}T${staff.working_hours.end}:00`,
            display: 'background',
            backgroundColor: 'rgba(16, 185, 129, 0.08)',
            groupId: 'businessHours',
          });
        }

        if (staff.appointments) {
          staff.appointments.forEach((app: any) => {
            this.allAppointments.push({ ...app, staff_name: staff.staff_name });
            const appDate = ((app.date ?? this.dashboardData.date) as string).substring(0, 10);
            events.push({
              id: String(app.id),
              resourceId: String(staff.staff_id),
              title: `${app.customer_name} - ${app.service_name}`,
              start: `${appDate}T${app.start}`,
              end: `${appDate}T${app.end}`,
              backgroundColor: this.getStatusColor(app.status_title),
              borderColor: 'transparent',
              extendedProps: { ...app, staff_name: staff.staff_name },
            });
          });
        }
      });

      this.allAppointments.sort((a, b) => a.start.localeCompare(b.start));

      const slotMin =
        Math.max(0, minHour - 1)
          .toString()
          .padStart(2, '0') + ':00:00';
      const slotMax =
        Math.min(24, maxHour + 1)
          .toString()
          .padStart(2, '0') + ':00:00';

      this.calendarOptions = {
        ...this.calendarOptions,
        resources: resources,
        events: events,
        slotMinTime: slotMin === '23:00:00' ? '08:00:00' : slotMin,
        slotMaxTime: slotMax === '01:00:00' ? '22:00:00' : slotMax,
      };

      this.cdr.detectChanges();
    }, 0);
  }

  onDatePickerChange(): void {
    const api = this.calendarComponent?.getApi();
    if (api) {
      api.gotoDate(this.selectedDate);
      // datesSet callback فراخوانی می‌شود → viewStart/viewEnd به‌روزرسانی و loadData صدا زده می‌شود
    } else {
      this.viewStart = new Date(this.selectedDate);
      this.viewEnd   = new Date(this.selectedDate);
      this.loadData();
    }
  }

  private loadDoctorSpecificData(): void {
    this.doctorHttp.getCurrentAppointment({ staff_id: this.staffId }).subscribe({
      next: (res: any) => {
        if (res.success && res.data) {
          this.currentAppointment = res.data;
          if (res.data.user?.id) this.loadCurrentPatientDetails(res.data.user.id);
        } else {
          this.currentAppointment = null;
        }
        this.cdr.markForCheck();
      },
      error: (err) => {
        console.error('Error fetching current appointment:', err);
        this.currentAppointment = null;
        this.cdr.markForCheck();
      },
    });
  }

  private loadCurrentPatientDetails(patientId: string | number): void {
    this.doctorHttp.getEchoHistoryByPatient(patientId).subscribe({
      next: (res: any) => {
        let defaultDetails = {
          name: this.currentAppointment.user?.name || '',
          mobile: this.currentAppointment.user?.mobile || '',
          echo_date: '-',
          details: 'هیچ اکو یافت نشد',
          file_address: '',
        };

        if (res.success && res.data && res.data.visits) {
          const visitsObj = res.data.visits;
          const dates = Object.keys(visitsObj).sort(
            (a, b) => new Date(b).getTime() - new Date(a).getTime(),
          );

          if (dates.length > 0) {
            const latestDate = dates[0];
            const latestVisit = visitsObj[latestDate][0];

            if (latestVisit) {
              const detailsParts = [];
              if (latestVisit.classification?.prediction)
                detailsParts.push(`View: ${latestVisit.classification.prediction}`);
              if (latestVisit.classification?.confidence !== undefined)
                detailsParts.push(
                  `Confidence: ${(latestVisit.classification.confidence * 100).toFixed(1)}%`,
                );
              if (latestVisit.measurements?.length > 0)
                detailsParts.push(`${latestVisit.measurements.length} measurements`);

              defaultDetails = {
                name: this.currentAppointment.user?.name || '',
                mobile: this.currentAppointment.user?.mobile || '',
                echo_date: latestDate,
                details: detailsParts.join(' | '),
                file_address:
                  latestVisit.files?.result_json_address ||
                  latestVisit.files?.classification_json_address ||
                  '',
              };
            }
          }
        }
        this.currentPatientDetails = defaultDetails;
        this.cdr.markForCheck();
      },
      error: (err) => {
        console.error('Error fetching patient details:', err);
        this.currentPatientDetails = {
          name: this.currentAppointment.user?.name || '',
          mobile: this.currentAppointment.user?.mobile || '',
          echo_date: '-',
          details: 'خطا در بارگذاری اطلاعات',
          file_address: '',
        };
        this.cdr.markForCheck();
      },
    });
  }

  private getStatusColor(status: string): string {
    const colors: Record<string, string> = {
      pending: '#f59e0b',
      confirmed: '#10b981',
      cancelled: '#ef4444',
      completed: '#6366f1',
    };
    return colors[status] || '#94a3b8';
  }

  viewEchoFile(file_address: string): void {
    if (!file_address) return;
    this.doctorHttp.getEchoFile(file_address).subscribe({
      next: (blob: Blob) => window.open(window.URL.createObjectURL(blob), '_blank'),
      error: () => this.toast.error(this.getTranslation('errorFetchingEchoFile')),
    });
  }

  getTranslation(key: string): string {
    return this.translationService.getTranslation(key);
  }

  calendarPrev() {
    const api = this.calendarComponent?.getApi();
    if (api) { api.prev(); this.calendarTitle = api.view.title; }
  }

  calendarNext() {
    const api = this.calendarComponent?.getApi();
    if (api) { api.next(); this.calendarTitle = api.view.title; }
  }

  calendarToday() {
    const api = this.calendarComponent?.getApi();
    if (api) { api.today(); this.calendarTitle = api.view.title; }
  }

  setCalendarView(view: string) {
    const api = this.calendarComponent?.getApi();
    if (api) {
      api.changeView(view);
      this.currentViewType = view;
      this.calendarTitle   = api.view.title;
    }
  }

  ngOnDestroy() {}

  onAppointmentClick(app: any): void {
    window.open(`/appointment?edit_id=${app.id}`, '_blank');
  }

  onAddAppointment(): void {
    window.open(`/appointment?`, '_blank');
  }
}
