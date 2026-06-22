import { Component, OnInit, inject, Inject, Optional } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatStepperModule } from '@angular/material/stepper';
import { ToastService } from '../../services/toast/toast.service';
import { AuthHTTPService } from '../../../auth/auth-http.service';

@Component({
  selector: 'app-patient-form',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatIconModule,
    MatTooltipModule,
    MatProgressSpinnerModule,
    MatStepperModule
  ],
  templateUrl: './patient-form.component.html',
  styleUrls: ['./patient-form.component.scss']
})
export class PatientFormComponent implements OnInit {
  private fb = inject(FormBuilder);
  private http = inject(HttpClient);
  private toast = inject(ToastService);
  
  basicInfoForm!: FormGroup;
  cardiovascularForm!: FormGroup;
  heartDiseaseForm!: FormGroup;
  lifestyleForm!: FormGroup;
  
  loading = false;
  userId: number | null = null;

  constructor(
    @Optional() public dialogRef: MatDialogRef<PatientFormComponent>,
    @Optional() @Inject(MAT_DIALOG_DATA) public data: any,
    private  authHttpService : AuthHTTPService ,
  ) {

    this.authHttpService.getMe().subscribe(response => {
      this.userId = response.data.id;
    });

    if (!this.userId && data?.userId) {
      this.userId = data.userId;
    }
  }

  ngOnInit(): void {
    this.initForms();
    if (this.userId) {
      this.loadExistingData();
    }
  }

  private initForms(): void {
    // بخش اطلاعات پایه
    this.basicInfoForm = this.fb.group({
      age: [null, [Validators.min(18), Validators.max(120)]],
      gender: [null],
      height: [null, [Validators.min(100), Validators.max(230)]],
      weight: [null, [Validators.min(30), Validators.max(250)]]
    });

    // بخش قلبی و عروقی (Cardiovascular Dataset)
    this.cardiovascularForm = this.fb.group({
      ap_hi: [null, [Validators.min(60), Validators.max(300)]],
      ap_lo: [null, [Validators.min(40), Validators.max(200)]],
      cholesterol: [null],
      gluc: [null]
    }, { validators: this.bloodPressureValidator });

    // بخش بیماری قلبی (Heart Disease Dataset)
    this.heartDiseaseForm = this.fb.group({
      cp: [null],
      trestbps: [null, [Validators.min(60), Validators.max(250)]],
      chol: [null, [Validators.min(100), Validators.max(600)]],
      fbs: [null],
      restecg: [null],
      thalach: [null, [Validators.min(40), Validators.max(220)]],
      exang: [null],
      oldpeak: [null, [Validators.min(0), Validators.max(6.2)]],
      slope: [null],
      ca: [null],
      thal: [null]
    });

    // بخش سبک زندگی
    this.lifestyleForm = this.fb.group({
      smoke: [null],
      alco: [null],
      active: [null]
    });
  }

  // Custom validator for blood pressure
  private bloodPressureValidator(group: FormGroup): { [key: string]: boolean } | null {
    const ap_hi = group.get('ap_hi')?.value;
    const ap_lo = group.get('ap_lo')?.value;
    
    if (ap_hi && ap_lo && ap_hi <= ap_lo) {
      return { invalidBloodPressure: true };
    }
    return null;
  }

  private loadExistingData(): void {
    this.loading = true;
    this.http.get(`/api/patient-profile/${this.userId}`).subscribe({
      next: (response: any) => {
        if (response.success && response.data) {
          this.populateForms(response.data);
        }
        this.loading = false;
      },
      error: (error) => {
        console.error('Error loading patient data:', error);
        this.loading = false;
      }
    });
  }

  private populateForms(data: any): void {
    // Map gender/sex back to UI format
    // From backend: sex=1 (male) or sex=0 (female)
    let genderUI = 'male'; // default
    if (data.sex === 0 || data.gender === 1) {
      genderUI = 'female';
    } else if (data.sex === 1 || data.gender === 2) {
      genderUI = 'male';
    }

    // Basic info
    this.basicInfoForm.patchValue({
      age: data.age,
      gender: genderUI,
      height: data.height,
      weight: data.weight
    });

    // Cardiovascular
    this.cardiovascularForm.patchValue({
      ap_hi: data.ap_hi,
      ap_lo: data.ap_lo,
      cholesterol: data.cholesterol,
      gluc: data.gluc
    });

    // Heart disease
    this.heartDiseaseForm.patchValue({
      cp: data.cp,
      trestbps: data.trestbps,
      chol: data.chol,
      fbs: data.fbs,
      restecg: data.restecg,
      thalach: data.thalach,
      exang: data.exang,
      oldpeak: data.oldpeak,
      slope: data.slope,
      ca: data.ca,
      thal: data.thal
    });

    // Lifestyle
    this.lifestyleForm.patchValue({
      smoke: data.smoke,
      alco: data.alco,
      active: data.active
    });
  }

  onSubmit(): void {
    // Mark all fields as touched to show validation errors
    Object.values(this.basicInfoForm.controls).forEach(control => control.markAsTouched());
    Object.values(this.cardiovascularForm.controls).forEach(control => control.markAsTouched());
    Object.values(this.heartDiseaseForm.controls).forEach(control => control.markAsTouched());
    Object.values(this.lifestyleForm.controls).forEach(control => control.markAsTouched());

    // Check for blood pressure validation error
    if (this.cardiovascularForm.hasError('invalidBloodPressure')) {
      this.toast.error('فشار خون سیستولیک باید بزرگتر از دیاستولیک باشد');
      return;
    }

    this.loading = true;

    // Combine all form data
    const formData = {
      ...this.basicInfoForm.value,
      ...this.cardiovascularForm.value,
      ...this.heartDiseaseForm.value,
      ...this.lifestyleForm.value
    };

    // Prepare data for backend - convert to numbers and handle null values
    const payload: any = {};
    
    // Extract gender before processing other fields
    const genderValue = formData.gender;
    
    // Process all numeric fields
    Object.keys(formData).forEach(key => {
      if (key === 'gender') return; // Skip gender, handle separately
      
      const value = formData[key];
      if (value !== null && value !== undefined && value !== '') {
        payload[key] = Number(value);
      }
    });

    // Map gender to correct values for both datasets
    // HD dataset: sex=1 (male) / sex=0 (female)
    // CV dataset: gender=2 (male) / gender=1 (female)
    if (genderValue === 'male' || genderValue === 'مرد') {
      payload.sex = 1;      // HD format: male=1
      payload.gender = 2;   // CV format: male=2
    } else if (genderValue === 'female' || genderValue === 'زن') {
      payload.sex = 0;      // HD format: female=0
      payload.gender = 1;   // CV format: female=1
    }

    // Add user_id if available
    if (this.userId) {
      payload.user_id = this.userId;
    }

    console.log('📤 Sending payload:', payload);

    this.http.post('/api/patient-profile/store', payload).subscribe({
      next: (response: any) => {
        this.toast.success('اطلاعات با موفقیت ذخیره شد');
        this.loading = false;
        if (this.dialogRef) {
          this.dialogRef.close({ success: true, data: response.data });
        }
      },
      error: (error) => {
        const errorMessage = error.error?.message || 'خطا در ذخیره اطلاعات';
        this.toast.error(errorMessage);
        this.loading = false;
      }
    });
  }

  toggleField(field: string, form: FormGroup): void {
    const current = form.get(field)?.value;
    form.get(field)?.setValue(current == 1 ? 0 : 1);
  }

  onCancel(): void {
    if (this.dialogRef) {
      this.dialogRef.close();
    }
  }
}
