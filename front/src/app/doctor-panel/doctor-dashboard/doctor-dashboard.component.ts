import { Component, OnInit, inject, ViewChild, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { MatProgressSpinner, MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { DoctorHttpService } from '../doctor-http.service';
import { ToastService } from '../../@shared/services/toast/toast.service';
import { TranslationService } from '../../@shared/services/translation.service';
import { format, parseISO } from 'date-fns';

// FullCalendar Imports
import { FullCalendarModule, FullCalendarComponent } from '@fullcalendar/angular';
import { CalendarOptions, EventInput } from '@fullcalendar/core';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import listPlugin from '@fullcalendar/list';
import interactionPlugin from '@fullcalendar/interaction';
import resourceTimelinePlugin from '@fullcalendar/resource-timeline';
import { MatCard, MatCardContent } from '@angular/material/card';
import { MatDivider } from '@angular/material/divider';

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
    FullCalendarModule,
    MatCardContent,
    MatCard,
    MatProgressSpinnerModule,
    MatDivider,
    MatProgressSpinner,
  ],
  templateUrl: './doctor-dashboard.component.html',
  styleUrls: ['./doctor-dashboard.component.scss'],
})
export class DoctorDashboardComponent implements OnInit {
  @ViewChild('calendar') calendarComponent!: FullCalendarComponent;

  private doctorHttp = inject(DoctorHttpService);
  private toast = inject(ToastService);
  private translationService = inject(TranslationService);
  private cdr = inject(ChangeDetectorRef);
  loading: any;
  selectedDate: Date = new Date();
  filterStaffIds: number[] = [];
  filterResourceIds: number[] = [];

  staffs: any[] = [];
  resources: any[] = [];
  dashboardData: any = null;
  allAppointments: any[] = [];
  isLoading = false;

  // Doctor-specific data
  currentAppointment: any = null;
  currentPatientDetails: any = null;
  staffId: number | null = null;

  // FullCalendar Options
  calendarOptions: CalendarOptions = {
    plugins: [resourceTimelinePlugin, interactionPlugin, dayGridPlugin, timeGridPlugin, listPlugin],
    initialView: 'resourceTimelineDay',
    headerToolbar: {
      left: 'prev,next today',
      center: 'title',
      right: 'resourceTimelineDay,timeGridWeek,dayGridMonth,listWeek',
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
    editable: false, // disable drag-and-drop for doctor view
    selectable: false,
    // Flexible constraints to allow "shooting" patients around (keep for background)
    eventConstraint: {
      startTime: '00:00',
      endTime: '24:00',
    },
    selectConstraint: {
      startTime: '00:00',
      endTime: '24:00',
    },
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
        subTitle.style.fontSize = '0.7rem';
        subTitle.style.color = '#64748b';
        subTitle.style.fontWeight = '400';
        subTitle.innerText = expertise;
        mainCell.appendChild(subTitle);
      }
    },
  };

  ngOnInit(): void {
    // Fetch current user to get staff id
    this.doctorHttp.getCurrentUser().subscribe({
      next: (res: any) => {
        if (res.success && res.data) {
          // Assuming user.id is the staff id
          this.staffId = res.data.id;
          this.loadInitialFilters(); // optional, we can skip
          this.loadData();
        }
      },
      error: (err) => {
        console.error('Error fetching current user:', err);
        this.isLoading = false;
        this.toast.error('خطا در دریافت اطلاعات کاربر');
      },
    });
  }

  loadInitialFilters(): void {
    // We can skip loading staff and resources as we hide filters.
    // Keep empty arrays.
    this.staffs = [];
    this.resources = [];
  }

  loadData(): void {
    if (this.staffId === null) {
      // Wait for staffId to be set
      return;
    }

    this.isLoading = true;

    const dateStr = format(this.selectedDate, 'yyyy-MM-dd');

    this.doctorHttp
      .getCalendarDashboard({
        date: dateStr,
        staff_ids: [this.staffId],
        // resource_ids: [] // optionally add resource filter if needed
      })
      .subscribe({
        next: (res: any) => {
          if (res.success && res.data) {
            this.dashboardData = res.data;
            this.isLoading = false;
            this.cdr.detectChanges(); // Trigger detection so @if is evaluated
            this.updateCalendarData();
            // Load doctor-specific data after calendar data is ready
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

    // Small timeout to ensure ViewChild is populated if @if just became true
    setTimeout(() => {
      const calendarApi = this.calendarComponent?.getApi();

      // 1. Prepare Resources (Staff)
      const resources = this.dashboardData.timeline.map((staff: any) => ({
        id: String(staff.staff_id),
        title: staff.staff_name,
        extendedProps: {
          expertise: staff.expertise,
          working_hours: staff.working_hours,
        },
      }));

      // 2. Prepare Events
      const events: EventInput[] = [];
      this.allAppointments = [];

      // Track min/max hours to adjust view
      let minHour = 24;
      let maxHour = 0;

      this.dashboardData.timeline.forEach((staff: any) => {
        // Update min/max from working hours
        if (staff.working_hours) {
          const startH = parseInt(staff.working_hours.start.split(':')[0]);
          const endH = parseInt(staff.working_hours.end.split(':')[0]);
          if (startH < minHour) minHour = startH;
          if (endH > maxHour) maxHour = endH;

          // Add Working Hours as Background (Green area)
          events.push({
            resourceId: String(staff.staff_id),
            start: `${this.dashboardData.date}T${staff.working_hours.start}:00`,
            end: `${this.dashboardData.date}T${staff.working_hours.end}:00`,
            display: 'background',
            backgroundColor: 'rgba(16, 185, 129, 0.12)', // Subtle green
            groupId: 'businessHours', // Constraint link
          });
        }

        if (staff.appointments) {
          staff.appointments.forEach((app: any) => {
            this.allAppointments.push({
              ...app,
              staff_name: staff.staff_name,
            });

            events.push({
              id: String(app.id),
              resourceId: String(staff.staff_id),
              title: `${app.customer_name} - ${app.service_name}`,
              start: `${this.dashboardData.date}T${app.start}`,
              end: `${this.dashboardData.date}T${app.end}`,
              backgroundColor: this.getStatusColor(app.status_title),
              borderColor: this.getStatusColor(app.status_title),
              extendedProps: {
                ...app,
                staff_name: staff.staff_name,
              },
            });
          });
        }
      });

      this.allAppointments.sort((a, b) => a.start.localeCompare(b.start));

      // Dynamic slot adjustment
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

      if (calendarApi) {
        calendarApi.gotoDate(this.dashboardData.date);
      }

      this.cdr.detectChanges();
    }, 0);
  }

  private loadDoctorSpecificData(): void {
    // Load current appointment
    this.doctorHttp.getCurrentAppointment({ staff_id: this.staffId }).subscribe({
      next: (res: any) => {
        if (res.success && res.data) {
          this.currentAppointment = res.data;
          if (res.data.user?.id) {
            this.loadCurrentPatientDetails(res.data.user.id);
          }
        }
        this.cdr.markForCheck();
      },
      error: (err) => {
        console.error('Error fetching current appointment:', err);
        this.cdr.markForCheck();
      },
    });
  }

  private loadCurrentPatientDetails(patientId: string | number): void {
    this.doctorHttp.getEchoHistoryByPatient(patientId).subscribe({
      next: (res: any) => {
        if (res.success && res.data) {
          const echoData = res.data;
          // Extract the latest visit from the visits object
          let latestVisit = null;
          let latestDate = '';
          const visitsObj = echoData.visits;
          if (visitsObj && typeof visitsObj === 'object') {
            const dates = Object.keys(visitsObj);
            if (dates.length > 0) {
              // Sort dates descending (most recent first)
              dates.sort((a, b) => new Date(b).getTime() - new Date(a).getTime());
              latestDate = dates[0];
              const visitArray = visitsObj[latestDate];
              if (Array.isArray(visitArray) && visitArray.length > 0) {
                // Take the first visit of the day (or we could sort by time within the day?)
                latestVisit = visitArray[0];
              }
            }
          }

          if (latestVisit) {
            // Build details string
            const detailsParts = [];
            if (latestVisit.classification?.prediction) {
              detailsParts.push(`View: ${latestVisit.classification.prediction}`);
            }
            if (latestVisit.classification?.confidence !== undefined) {
              detailsParts.push(`Confidence: ${(latestVisit.classification.confidence * 100).toFixed(1)}%`);
            }
            if (latestVisit.measurements && latestVisit.measurements.length > 0) {
              detailsParts.push(`${latestVisit.measurements.length} measurements`);
            }
            const details = detailsParts.join(' | ');

            // Get file address for viewing/downloading (prefer result_json)
            let fileAddress = '';
            if (latestVisit.files && latestVisit.files.result_json_address) {
              fileAddress = latestVisit.files.result_json_address;
            } else if (latestVisit.files && latestVisit.files.classification_json_address) {
              fileAddress = latestVisit.files.classification_json_address;
            }

            // Build patient details object combining user info from current appointment and echo details
            this.currentPatientDetails = {
              name: this.currentAppointment.user?.name || '',
              mobile: this.currentAppointment.user?.mobile || '',
              echo_date: latestDate,
              details: details,
              file_address: fileAddress
            };
          } else {
            // No visits found
            this.currentPatientDetails = {
              name: this.currentAppointment.user?.name || '',
              mobile: this.currentAppointment.user?.mobile || '',
              echo_date: '-',
              details: 'هیچ اکو یافت نشد',
              file_address: ''
            };
          }
        } else {
          // No echo history data
          this.currentPatientDetails = {
            name: this.currentAppointment.user?.name || '',
            mobile: this.currentAppointment.user?.mobile || '',
            echo_date: '-',
            details: 'هیچ اکو یافت نشد',
            file_address: ''
          };
        }
        this.cdr.markForCheck();
      },
      error: (err) => {
        console.error('Error fetching patient details:', err);
        // On error, still show the user info but with error state for echo
        this.currentPatientDetails = {
          name: this.currentAppointment.user?.name || '',
          mobile: this.currentAppointment.user?.mobile || '',
          echo_date: '-',
          details: 'خطا در بارگذاری اطلاعات اکو',
          file_address: ''
        };
        this.cdr.markForCheck();
      }
    });
  }

  private getStatusColor(status: string): string {
    switch (status) {
      case 'pending':
        return '#f59e0b';
      case 'confirmed':
        return '#10b981';
      case 'cancelled':
        return '#ef4444';
      case 'completed':
        return '#6366f1';
      default:
        return '#94a3b8';
    }
  }

  viewEchoFile(file_address: string): void {
    if (file_address) {
      this.doctorHttp.getEchoFile(file_address).subscribe({
        next: (blob: Blob) => {
          const url = window.URL.createObjectURL(blob);
          window.open(url, '_blank');
        },
        error: (err) => {
          this.toast.error(this.getTranslation('errorFetchingEchoFile'));
        }
      });
    }
  }

  getTranslation(key: string): string {
    return this.translationService.getTranslation(key);
  }

  onAppointmentClick(app: any): void {
    window.open(`/appointment?edit_id=${app.id}`, '_blank');
  }

  onAddAppointment(): void {
    window.open(`/appointment?`, '_blank');
  }
}