import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { TranslationService } from '../../@shared/services/translation.service';
import { AuthService } from '../../auth/auth.service';
import { AuthHTTPService } from '../../auth/auth-http.service';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatButtonModule,
    MatIconModule,
    MatCardModule,
    MatChipsModule,
  ],
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.scss'],
})
export class HomeComponent implements OnInit {
  private authService = inject(AuthService);
  private authhttpService = inject(AuthHTTPService);
  private translationService = inject(TranslationService);
  userRole: string | null = null;
  userName: string | null = null;

  ngOnInit() {
    this.loadUserInfo();
  }

  loadUserInfo() {
    this.authhttpService.getMe().subscribe({
      next: (response: any) => {
        if (response.success && response.data) {
          this.userRole = response.data.role;
          this.userName = response.data.name;
        }
      },
      error: () => {
        this.userRole = null;
        this.userName = null;
      },
    });
  }

  getTranslation(key: string): string {
    return this.translationService.getTranslation(key);
  }

  isRTL(): boolean {
    return this.translationService.getCurrentLang() === 'fa';
  }
}
