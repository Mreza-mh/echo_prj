import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDividerModule } from '@angular/material/divider';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { FormsModule } from '@angular/forms';
import { MatSelectModule } from '@angular/material/select';
import { DoctorHttpService } from '../doctor-http.service';
import { ToastService } from '../../@shared/services/toast/toast.service';
import { TranslationService } from '../../@shared/services/translation.service';
import { MatExpansionPanel, MatExpansionPanelDescription, MatExpansionPanelHeader, MatExpansionPanelTitle } from '@angular/material/expansion';
import { MatTabNavPanel } from '@angular/material/tabs';
import { MatDialogModule } from '@angular/material/dialog';
import { MatDialog } from '@angular/material/dialog';
import { ImageViewerDialogComponent } from './image-viewer-dialog.component';
import { HeartVisualizationComponent } from '../../index/heart-visualization/heart-visualization';

@Component({
  selector: 'app-echo-history',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatDividerModule,
    MatTooltipModule,
    MatFormFieldModule,
    MatInputModule,
    FormsModule,
    MatSelectModule,
    MatExpansionPanelDescription,
    MatExpansionPanelTitle,
    MatExpansionPanel,
    MatExpansionPanelHeader,
    MatDialogModule,
    ImageViewerDialogComponent,
    HeartVisualizationComponent
  ],
  templateUrl: './echo-history.component.html',
  styleUrls: ['./echo-history.component.scss'],
})
export class EchoHistoryComponent implements OnInit {
  private doctorHttp = inject(DoctorHttpService);
  private toast = inject(ToastService);
  private translationService = inject(TranslationService);
  private dialog = inject(MatDialog);

  echoData: any = null;
  loading = true;
  error: string | null = null;
  patientId: string | number | null = null;
  searchPatientId: string | number = '';

  // Processed data for display
  patientInfo: any = null;
  visitDates: string[] = []; // sorted descending
  visitsByDate: { [date: string]: any[] } = {};
  selectedDate: string = '';

  ngOnInit(): void {
    // Initially, we don't load any echo history until a patient is searched
    this.echoData = null;
    this.loading = false;
  }

  searchPatient(): void {
    const id = Number(this.searchPatientId);
    if (isNaN(id)) {
      this.toast.error(this.getTranslation('pleaseEnterValidPatientId'));
      return;
    }
    this.patientId = id;
    this.loadEchoHistory();
  }

  loadEchoHistory(): void {
    if (this.patientId === null) {
      this.echoData = null;
      this.patientInfo = null;
      this.visitDates = [];
      this.visitsByDate = {};
      this.selectedDate = '';
      this.loading = false;
      return;
    }

    this.loading = true;
    this.error = null;
    this.echoData = null;
    this.patientInfo = null;
    this.visitDates = [];
    this.visitsByDate = {};
    this.selectedDate = '';

    this.doctorHttp.getEchoHistoryByPatient(this.patientId).subscribe({
      next: (response: any) => {
        if (response.success && response.data) {
          this.echoData = response.data;
          this.processEchoData();
        } else {
          this.echoData = null;
          this.error = this.getTranslation('noEchoHistoryFoundForPatient');
        }
        this.loading = false;
      },
      error: (err) => {
        console.error('Error fetching echo history:', err);
        this.error = this.getTranslation('errorFetchingEchoHistory');
        this.loading = false;
      },
    });
  }

  private processEchoData(): void {
    if (!this.echoData) return;
    this.patientInfo = this.echoData.patient_info || {};
    const visits = this.echoData.visits || {};
    this.visitDates = Object.keys(visits).sort(
      (a, b) => new Date(b).getTime() - new Date(a).getTime(),
    );
    this.visitsByDate = visits;
    if (this.visitDates.length > 0) {
      this.selectedDate = this.visitDates[0];
    }
  }

  refresh(): void {
    this.loadEchoHistory();
  }

  getVisitList(date: string): any[] {
    return this.visitsByDate[date] || [];
  }

  getTranslation(key: string): string {
    return this.translationService.getTranslation(key);
  }

  // Helper to check if a value is boolean (to hide in UI)
  isBoolean(val: any): boolean {
    return typeof val === 'boolean';
  }

  viewFile(address: string): void {
    if (address) {
      this.dialog.open(ImageViewerDialogComponent, {
        data: { imageUrl: address },
        width: '90%',
        maxWidth: '600px',
        height: '90%',
        maxHeight: '700px',
      });
    }
  }
}