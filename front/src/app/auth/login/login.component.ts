import { Component, OnInit, ChangeDetectorRef, NgZone } from '@angular/core';
import { Router } from '@angular/router';
import {
  FormBuilder,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { CommonModule } from '@angular/common';
import { AuthHTTPService } from '../auth-http.service';
import { AuthService } from '../auth.service';
import { ToastService } from '../../@shared/services/toast/toast.service';
@Component({
  selector: 'app-login',
  imports: [CommonModule, FormsModule, ReactiveFormsModule],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss'],
})
export class LoginComponent implements OnInit {
  currentStep: 'MOBILE' | 'VERIFY' | 'PASSWORD' | 'SET_PASSWORD' | 'FORGOT' = 'MOBILE';
  has_password = false;
  isLoading: boolean = false;
  checkMobileForm!: FormGroup;
  verificationCodeForm!: FormGroup;
  setPasswordForm!: FormGroup;
  passwordForm!: FormGroup;
  isMobileEntered: boolean = false;
  forgotPasswordForm!: FormGroup;

  constructor(
    private router: Router,
    private fb: FormBuilder,
    private toastService: ToastService,
    private authHTTPService: AuthHTTPService,
    private authService: AuthService,
    private cdr: ChangeDetectorRef,
    private ngZone: NgZone,
  ) {
    this.createLoginForm();
    this.createVerifyCodeForm();
    this.createPasswordForm();
    this.createSetPasswordForm();
    this.createForgotPasswordForm();
  }
  ngOnInit(): void {}

  OnEditMobile() {
    this.reseAllForms();
    this.isMobileEntered = false;
    this.currentStep = 'MOBILE';
    this.cdr.detectChanges();
  }

  reseAllForms() {
    this.checkMobileForm.reset(); // Clear mobile number
    this.checkMobileForm.enable(); // Enable input field
    this.verificationCodeForm.reset(); // Reset verification form
    this.passwordForm.reset(); // Reset password form
  }

  timer: number = 0;
  displayedTimer: string = '02:00';
  resendDisabled: boolean = true;

  startTimer() {
    this.timer = 120;
    this.resendDisabled = true;
    this.ngZone.runOutsideAngular(() => {
      const interval = setInterval(() => {
        this.ngZone.run(() => {
          if (this.timer <= 0) {
            clearInterval(interval);
            this.timer = 0;
            this.displayedTimer = '00:00';
            this.resendDisabled = false;
            this.cdr.detectChanges();
            return;
          }

          this.timer--;
          const minutes = Math.floor(this.timer / 60);
          const seconds = this.timer % 60;
          this.displayedTimer = `${this.formatTime(minutes)}:${this.formatTime(seconds)}`;
          this.cdr.detectChanges();
        });
      }, 1000);
    });
    this.resendDisabled = true; // Disable resend button when timer starts
  }

  formatTime(time: number): string {
    return time < 10 ? `0${time}` : `${time}`;
  }

  passwordFieldType: string = 'password';
  passwordSecondFieldType: string = 'password';

  togglePasswordSecondVisibility() {
    this.passwordSecondFieldType =
      this.passwordSecondFieldType === 'password' ? 'text' : 'password';
  }

  oldUserLoginWithPasswordButton() {
    this.currentStep = 'VERIFY';
    this.sendMobileNumberToAPI();
  }
  forgotPassword() {
    this.currentStep = 'FORGOT';
    this.sendMobileNumberToAPI();
    this.forgotPasswordForm.get('email')?.setValue(this.checkMobileForm.value.email);
  }

  sendMobileNumberToAPI() {
    this.isLoading = true;
    if (this.checkMobileForm.invalid) {
      this.toastService.error('ایمیل نا معتبر است');
      this.isLoading = false;
      return;
    }
    this.checkMobileForm.get('email')?.disable();

    const data = {
      email: this.checkMobileForm.value.email,
    };

    this.authHTTPService.checkmoobile(data).subscribe({
      next: (response) => {
        // console.log(response);

        this.has_password = response.data.has_password;
        console.log(!response.data.force_by_sms);
        console.log(this.currentStep === 'FORGOT');
        /// for handling which pop up to show
        // based  on the response comes from backend
        console.log(
          this.has_password && !response.data.force_by_sms && this.currentStep !== 'FORGOT',
        );

        if (!this.has_password && this.currentStep !== 'FORGOT') {
          this.currentStep = 'VERIFY';
          console.log(this.currentStep);
          this.isMobileEntered = true;
          this.startTimer();
          this.cdr.detectChanges(); // Force change detection
        }
        if (this.has_password && !response.data.force_by_sms && this.currentStep !== 'FORGOT') {
          this.currentStep = 'PASSWORD';
          this.isMobileEntered = true;
          this.cdr.detectChanges();
        }
        if (this.has_password && response.data.force_by_sms && this.currentStep !== 'FORGOT') {
          this.currentStep = 'VERIFY';
          this.isMobileEntered = true;
          this.startTimer();
          this.cdr.detectChanges();
        }
      },
      error: (err) => {
        console.log('error in component', err);
        this.isLoading = false;
        this.checkMobileForm.get('email')?.enable();
        this.toastService.error(err);
      },
      complete: () => {
        this.isLoading = false;
        this.cdr.detectChanges();
      },
    });
  }

  email: string = '';
  processVerificationCode() {
    this.isLoading = true;
    if (this.verificationCodeForm.invalid) {
      this.toastService.error(' کد تایید فرمت درستی ندارد');
      this.isLoading = false;
      return;
    }

    this.email = this.checkMobileForm.value.email;
    const requestData = {
      email: this.checkMobileForm.value.email,
      verification_code: this.verificationCodeForm.get('verifyCode')?.value,
    };

    this.authService.confirmCode(requestData).subscribe({
      next: (response) => {
        console.log('response  : ' + response);
        this.toastService.success(response.message);

        console.log('in response to confirm code ', this.has_password);
        if (this.has_password) {
          this.router.navigateByUrl('/');
        } else {
          this.currentStep = 'SET_PASSWORD';
          this.cdr.detectChanges();
        }
      },
      error: (err) => {
        this.isLoading = false;
        this.verificationCodeForm.get('verifyCode')?.enable();
        this.toastService.error(err.message || 'خطای ناشناخته');
        this.cdr.detectChanges();
      },
      complete: () => {
        this.isLoading = false;
        this.cdr.detectChanges();
      },
    });
  }

  resendVerifyCode() {
    this.isLoading = true;
    if (this.timer > 0) {
      return;
    }
    this.authHTTPService
      .resendConfirmCode({
        email: this.checkMobileForm.get('email')?.value,
      })
      .subscribe({
        next: (data: any) => {
          console.log(data);
          this.startTimer();
          this.toastService.success(data.message || 'کد تایید با موفقیت ارسال شد!');
        },
        error: (err) => {
          this.isLoading = false;
          this.toastService.error(err.message || 'خطای ناشناخته');
        },
        complete: () => {
          this.isLoading = false;
        },
      });
  }

  // API Call for sending password
  LoginWithPassword() {
    console.log('a;shdf');

    this.isLoading = true;
    if (this.passwordForm.invalid) {
      this.toastService.error('فرم را به درستی پر کنید');
      this.isLoading = false;
      return;
    }
    const data = {
      email: this.checkMobileForm.value.email,
      password: this.passwordForm.value.password,
    };
    this.authService.loginPassword(data).subscribe({
      next: (response: any) => {
        this.toastService.success(response.message || 'ورود موفق');
        this.router.navigateByUrl('/');
      },
      error: (err: any) => {
        this.toastService.error(err || 'خطای ناشناخته');
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      complete: () => {
        this.isLoading = false;
        this.cdr.detectChanges();
      },
    });
  }

  isPasswordVisible = false;
  togglePasswordVisibility() {
    this.isPasswordVisible = !this.isPasswordVisible;
  }

  get verifyCodeControl() {
    return this.verificationCodeForm.get('verifyCode');
  }

  OnSetPassword() {
    this.isLoading = true;
    if (this.setPasswordForm.invalid) {
      this.toastService.error('اطلاعات نا معتبر است');
      this.isLoading = false;
      return;
    }

    const data = {
      password: this.setPasswordForm.get('password')?.value,
      email: this.email,
    };

    console.log('on set password');
    this.authHTTPService.setPassword(data).subscribe({
      next: (data: any) => {
        this.toastService.success(data.message || 'ثبت شد!');
        this.router.navigateByUrl('/');
      },
      error: (err: any) => {
        this.toastService.error(err.message || 'خطای ناشناخته');
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      complete: () => {
        this.isLoading = false;
        this.cdr.detectChanges();
      },
    });
  }

  onResetPassword() {
    this.isLoading = true;
    if (this.forgotPasswordForm.invalid) {
      this.toastService.error('اطلاعات نا معتبر است');
      this.isLoading = false;
      return;
    }
    console.log(this.forgotPasswordForm.value);

    if (
      this.forgotPasswordForm.get('password')?.value !==
      this.forgotPasswordForm.get('password_confirmation')?.value
    ) {
      this.toastService.error('گذرواژه ی جدید با تایید گذرواژه برابر نیست!');
      this.isLoading = false;
      return;
    }

    const requestData = {
      email: this.forgotPasswordForm.get('email')?.value,
      verification_code: this.forgotPasswordForm.get('verification_code')?.value,
      password: this.forgotPasswordForm.get('password')?.value,
    };

    this.authHTTPService.resetPassword(requestData).subscribe({
      next: (data: any) => {
        this.toastService.success(data.message || 'ثبت شد!');
        this.currentStep = 'MOBILE';
        this.cdr.detectChanges();
      },
      error: (err: any) => {
        this.toastService.error(err.message || 'خطای ناشناخته');
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      complete: () => {
        this.isLoading = false;
        this.cdr.detectChanges();
      },
    });
  }

  private createForgotPasswordForm() {
    this.forgotPasswordForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: [
        '',
        [
          Validators.required,
          Validators.minLength(6),
          Validators.pattern(/^[a-zA-Z0-9!@#$%^&*()-_+=?<>]+$/),
        ],
      ],
      password_confirmation: [
        '',
        [
          Validators.required,
          Validators.minLength(6),
          Validators.pattern(/^[a-zA-Z0-9!@#$%^&*()-_+=?<>]+$/),
        ],
      ],
      verification_code: ['', [Validators.required, Validators.pattern(/^\d{4,8}$/)]],
    });
  }
  private createSetPasswordForm() {
    this.setPasswordForm = this.fb.group({
      password: [
        '',
        [
          Validators.required,
          Validators.minLength(6),
          Validators.pattern(/^[a-zA-Z0-9!@#$%^&*()-_+=?<>]+$/),
        ],
      ],
      passwordC: [
        '',
        [
          Validators.required,
          Validators.minLength(6),
          Validators.pattern(/^[a-zA-Z0-9!@#$%^&*()-_+=?<>]+$/),
        ],
      ],
    });
  }
  private createPasswordForm() {
    this.passwordForm = this.fb.group({
      password: [
        '',
        [
          Validators.required,
          Validators.minLength(6),
          Validators.pattern(/^[a-zA-Z0-9!@#$%^&*()-_+=?<>]+$/),
        ],
      ],
    });
  }
  private createLoginForm() {
    this.checkMobileForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
    });
  }

  private createVerifyCodeForm() {
    this.verificationCodeForm = this.fb.group({
      verifyCode: ['', [Validators.required, Validators.pattern(/^\d{4,8}$/)]],
    });
  }
}
